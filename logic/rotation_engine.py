"""
Rotations-Engine mit festen Paarungen, Pflicht-Füllern, Beliebtheit
und Leer-/Befüllvorschlägen.

FIX v0.2.3:
- Alle RuleEngine-Aufrufe erhalten die bereits offene Session →
  kein Session-Leak mehr.
- check() wird pro Kombination nur noch einmal aufgerufen; der Score
  wird mit den bereits berechneten Violations berechnet.
- Farb-Duplikat-Prüfung: Tinten aus bereits aktiver Farbfamilie werden
  in Vorschlägen übersprungen (laut Briefing: Farbspektrum-Logik).
"""
import logging
import random
from datetime import datetime
from typing import List, Dict, Any

from database.db import get_session
from database.models import Pen, Ink, InkLoad, AppSettings
from logic.rule_engine import RuleEngine, LEVEL_ICONS
from logic.color_family_service import normalize_color_family
from logic.event_bus import AppEventBus
from logic.auto_mode_service import AutoModeService, action_label
from logic.enthusiast_lab_service import apply_ink_consumption
from logic.role_config import (load_role_configs, score_ink_for_role,
                               load_theme_configs, score_ink_for_theme)
from i18n.translator import format_date, t

_log = logging.getLogger(__name__)


BLOCKING_STATUSES = {"problem", "service", "blocked", "dry_risk"}

FILL_SYSTEM_KEYS = {
    "piston": "pen.fill_systems.piston",
    "vac": "pen.fill_systems.vac",
    "converter": "pen.fill_systems.converter",
    "cartridge": "pen.fill_systems.cartridge",
    "eyedropper": "pen.fill_systems.eyedropper",
}


def _fill_system_label(fill_system: str | None) -> str:
    raw = fill_system or ""
    key = FILL_SYSTEM_KEYS.get(raw, "")
    if not key:
        return raw
    label = t(key)
    return raw if label == key else label

# ── Farb-Distanz ──────────────────────────────────────────────────────────────

def _hex_to_rgb(hex_str: str) -> tuple:
    h = (hex_str or "#888888").lstrip("#")
    if len(h) != 6:
        return (128, 128, 128)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _color_distance(hex1: str, hex2: str) -> float:
    """Euklidische RGB-Distanz, Maximum ~441."""
    r1, g1, b1 = _hex_to_rgb(hex1)
    r2, g2, b2 = _hex_to_rgb(hex2)
    return ((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2) ** 0.5


# ── Rollen-/Themen-Inferenz ───────────────────────────────────────────────────

_FINE_NIB_SIZES  = {"EF", "XXF", "UEF", "XXXF"}
_BROAD_NIB_SIZES = {"B", "BB", "BBB", "2B", "3B"}
_STUB_KEYWORDS   = {"stub", "italic", "cursive", "oblique", "zoom"}






def _split_csv(value) -> set[str]:
    if not value:
        return set()
    if isinstance(value, (list, tuple, set)):
        raw = value
    else:
        raw = str(value).split(",")
    return {str(v).strip().lower() for v in raw if str(v).strip()}



def _role_label(role: str) -> str:
    key = f"rotation.role_{role}"
    lbl = t(key)
    return (role or "—") if lbl == key else lbl


def _theme_label(theme: str | None) -> str:
    if not theme:
        return "—"
    key = f"rotation.theme_{theme}"
    lbl = t(key)
    return theme if lbl == key else lbl


def _infer_pen_role(pen) -> str:
    """Ermittelt die Rotationsrolle.

    Priorität:
    1. explizite Nicht-Writer-Rolle aus der UI (harte Vorgabe)
    2. bestehende Tags (problem/grail/collector/vintage)
    3. Pflichtstatus (must_include_in_rotation)
    4. Feder-/Schliff-Fallback für alte Datensätze
    5. writer (generischer Default)
    """
    explicit = (getattr(pen, "rotation_role", None) or "").strip().lower()
    # Release-Fix: Alte Datensätze haben oft rotation_role="writer" ohne dass der
    # Nutzer bewusst eine Rolle gewählt hat. Nur eine explizite Nicht-Writer-Rolle
    # gilt als harte Vorgabe; Tags/Pflichtstatus/Feder dürfen "writer" übersteuern.
    if explicit and explicit != "writer":
        return explicit

    tags = _split_csv(getattr(pen, "tags", None))
    if "problem" in tags:
        return "problem"
    if "grail" in tags or "collector" in tags:
        return "collector"
    if "vintage" in tags:
        return "vintage"
    if getattr(pen, "must_include_in_rotation", False):
        return "must"

    setup = getattr(pen, "active_nib_setup", None)
    nib   = getattr(setup, "nib", None) or getattr(pen, "nib", None)
    nib_size = (getattr(nib, "size", "") or "").strip().upper()
    grind = (getattr(nib, "grind", "") or "").strip().lower()
    if nib_size in _FINE_NIB_SIZES:
        return "fine"
    if nib_size in _BROAD_NIB_SIZES or any((k in nib_size.lower()) or (k in grind) for k in _STUB_KEYWORDS):
        return "broad"
    return "writer"



class RotationEngine:
    def __init__(self):
        self.rule_engine = RuleEngine()

    # ------------------------------------------------------------------ #
    # Vorschläge für leere Füller                                         #
    # ------------------------------------------------------------------ #
    def _last_used_days(self, pen) -> int:
        """Tage seit letzter Nutzung/Reinigung. Leere Füller ohne Historie bekommen Bonus."""
        try:
            loads = list(getattr(pen, "ink_loads", []) or [])
            if not loads:
                return 999
            last = max((l.cleaned_date or l.loaded_date) for l in loads if l.loaded_date)
            return max(0, (datetime.now() - last).days)
        except Exception:
            _log.exception("Fehler bei _last_used_days")
            return 0

    def _ink_last_used_days(self, ink) -> int:
        """Tage seit die Tinte zuletzt in IRGENDEINEM Füller eingefüllt war.
        Rückgabe 999 = nie benutzt (höchste Priorität).
        """
        try:
            loads = list(getattr(ink, "ink_loads", []) or [])
            if not loads:
                return 999
            last = max((l.cleaned_date or l.loaded_date) for l in loads if l.loaded_date)
            return max(0, (datetime.now() - last).days)
        except Exception:
            _log.exception("Fehler bei _ink_last_used_days")
            return 0

    def _ink_last_used_bonus(self, ink_days: int) -> int:
        """Tinten-Standzeit-Bonus: zentrale Metrik für Tinten-Rotation."""
        if ink_days >= 999:
            return 90   # nie benutzt
        if ink_days >= 180:
            return 75   # >6 Monate
        if ink_days >= 90:
            return 50   # >3 Monate
        if ink_days >= 30:
            return 25   # >1 Monat
        if ink_days >= 14:
            return 10   # 2 Wochen
        return 0

    def _color_family_penalty(self, ink, active_color_families: set, is_fixed_pairing: bool) -> tuple[int, str]:
        """Farbspektrum ist wichtig, aber darf leere Füller nicht komplett blockieren."""
        fam = normalize_color_family(getattr(ink, "color_family", None)) or ""
        if not fam or is_fixed_pairing:
            return 0, ""
        if fam in active_color_families:
            return -18, t("rotation.color_family_active")
        return 14, t("rotation.color_spectrum_new")

    def _cleaning_safety_score(self, pen, ink) -> tuple[int, list[str]]:
        """Zusätzliche Sicherheitsgewichtung für Reinigung/Wartung."""
        score = 0
        hints: list[str] = []
        cleaning = getattr(ink, "cleaning_effort", 3) or 3
        sheen = getattr(ink, "sheen_level", 0) or 0
        shimmer = bool(getattr(ink, "has_shimmer", False))
        pigment = bool(getattr(ink, "is_pigment", False))
        fill_system = getattr(pen, "fill_system", "") or ""
        score -= max(0, cleaning - 3) * 8
        if cleaning >= 4:
            hints.append(t("rotation.clean_harder"))
        if sheen >= 4:
            score -= 10
            hints.append(t("rotation.strong_sheen"))
        if shimmer:
            score -= 25
            hints.append(t("rotation.shimmer_risk"))
        if pigment:
            score -= 20
            hints.append(t("rotation.pigment_risk"))
        if fill_system == "vac" and (shimmer or pigment or sheen >= 4 or cleaning >= 4):
            score -= 35
            hints.append(t("rotation.vac_difficult"))
        return score, hints

    def _paper_context_score(self, pen, ink, paper) -> tuple[int, list[str]]:
        """Papier-Kontext beeinflusst Score: Feathering-Risiko, Sheen-Eignung."""
        if paper is None:
            return 0, []
        score = 0
        hints: list[str] = []

        setup = getattr(pen, "active_nib_setup", None)
        nib = getattr(setup, "nib", None) or getattr(pen, "nib", None)
        nib_size = (getattr(nib, "size", "") or "").upper().strip() if nib else ""
        feathering = getattr(paper, "feathering_level", 2) or 2
        sheen_suitability = getattr(paper, "sheen_suitable", None)
        paper_name = f"{getattr(paper, 'brand', '')} {getattr(paper, 'name', '')}".strip()

        if nib_size == "EF" and feathering >= 4:
            score -= 20
            hints.append(t("rotation.paper_ef_feather", n=feathering, paper=paper_name))

        wetness = getattr(ink, "wetness_level", 3) or 3
        if feathering >= 4 and wetness >= 4:
            score -= 15
            hints.append(t("rotation.paper_wet_feather", paper=paper_name))

        if getattr(ink, "has_sheen", False) and sheen_suitability is True:
            score += 12
            hints.append(t("rotation.paper_sheen_good", paper=paper_name))
        elif getattr(ink, "has_sheen", False) and sheen_suitability is False:
            score -= 10
            hints.append(t("rotation.paper_sheen_limited", paper=paper_name))

        if getattr(ink, "has_shimmer", False) and feathering >= 4:
            score -= 10
            hints.append(t("rotation.paper_shimmer_spread"))

        return score, hints

    def _active_rotation_context(self, session, *, exclude_pen_id: int | None = None) -> tuple[set, set, list]:
        """Aktive Tinten/Farben für Duplikat- und Farbspektrum-Bewertung."""
        active_ink_ids: set = set()
        active_color_families: set = set()
        active_color_hexes: list = []
        for p in session.query(Pen).filter_by(is_active=True).all():
            if exclude_pen_id is not None and p.id == exclude_pen_id:
                continue
            if p.current_ink_load:
                active_ink_ids.add(p.current_ink_load.ink_id)
                ink = session.get(Ink, p.current_ink_load.ink_id)
                if ink:
                    if ink.color_family:
                        active_color_families.add(normalize_color_family(ink.color_family) or ink.color_family.lower())
                    if ink.color_hex:
                        active_color_hexes.append(ink.color_hex)
        return active_ink_ids, active_color_families, active_color_hexes

    def _load_paper(self, session, paper_id: int | None):
        if paper_id is None:
            return None
        from database.models import Paper
        return session.get(Paper, paper_id)

    def _score_pen_ink(
        self,
        pen,
        ink,
        session,
        *,
        active_ink_ids: set,
        active_color_families: set,
        paper=None,
        theme: str | None = None,
        empty_bonus: int = 120,
        current_ink_id: int | None = None,
        clean_refill: bool = False,
        role_configs: dict | None = None,
        theme_configs: dict | None = None,
    ) -> Dict[str, Any]:
        """Einheitliche Scoring-Logik für Vorschläge und Clean+Refill."""
        is_fixed_pairing = (pen.fixed_ink_id == ink.id)
        violations = self.rule_engine.check(pen, ink, session)
        rule_score = self.rule_engine.score(pen, ink, violations, session)
        has_blocking_rule = self.rule_engine.has_blocking_violation(violations)

        ink_days = self._ink_last_used_days(ink)
        ink_last_used_bonus = self._ink_last_used_bonus(ink_days)
        last_days = self._last_used_days(pen)
        pen_last_used_bonus = 0 if clean_refill else (min(80, int(last_days / 2)) if last_days < 999 else 80)
        popularity = getattr(pen, "popularity_rating", 3) or 3
        popularity_bonus = 0  # steckt bereits in RuleEngine.score(); nicht doppelt zählen

        pen_role = _infer_pen_role(pen)
        effective_theme = (theme or getattr(pen, "rotation_theme", None) or "").strip().lower() or None
        fill_system = getattr(pen, "fill_system", "") or ""
        _nib_setup   = getattr(pen, "active_nib_setup", None)
        _nib_obj     = getattr(_nib_setup, "nib", None) or getattr(pen, "nib", None)
        pen_nib_size = (getattr(_nib_obj, "size", "") or "").strip()

        color_delta, color_hint = self._color_family_penalty(ink, active_color_families, is_fixed_pairing)
        clean_delta, clean_hints = self._cleaning_safety_score(pen, ink)
        paper_delta, paper_hints = self._paper_context_score(pen, ink, paper)
        role_delta, role_hints = score_ink_for_role(pen_role, ink, fill_system, role_configs, nib_size=pen_nib_size)
        theme_delta, theme_hints = score_ink_for_theme(effective_theme, ink, fill_system, theme_configs, nib_size=pen_nib_size)

        duplicate_penalty = 0
        duplicate_hint = ""
        if ink.id in active_ink_ids and ink.id != current_ink_id and not is_fixed_pairing:
            duplicate_penalty = -22
            duplicate_hint = t("rotation.ink_already_active")

        fixed_bonus = 0
        must_bonus = 0

        score = (
            rule_score
            + empty_bonus
            + pen_last_used_bonus
            + ink_last_used_bonus
            + popularity_bonus
            + color_delta
            + clean_delta
            + paper_delta
            + role_delta
            + theme_delta
            + duplicate_penalty
            + fixed_bonus
            + must_bonus
        )

        warning_texts = [
            f"{LEVEL_ICONS.get(v.warn_level, '⚠')} {v.rule_name}: {v.description}" + (t("rotation.warning_hard_rule_suffix") if v.rule_type == "hard" and v.warn_level != "blocked" else "")
            for v in violations
            if v.warn_level in ("blocked", "critical", "warning") or v.rule_type == "hard"
        ]
        if has_blocking_rule and not is_fixed_pairing:
            score = min(score, -50)
        auto_decision = AutoModeService.decide(session, pen, ink, violations, int(score))
        if auto_decision.enabled and auto_decision.action == "reject":
            score = min(score, -999)

        hints: list[str] = []
        hints.append(t("rotation.hint_refill") if clean_refill else t("rotation.hint_empty"))
        hints.append(t("rotation.hint_role_prefix", label=_role_label(pen_role)))
        if effective_theme:
            hints.append(t("rotation.hint_theme_prefix", label=_theme_label(effective_theme)))
        if not clean_refill:
            if last_days >= 999:
                hints.append(t("rotation.hint_pen_never"))
            elif last_days >= 30:
                hints.append(t("rotation.hint_pen_empty_days", n=last_days))
        if ink_days >= 999:
            hints.append(t("rotation.hint_ink_never"))
        elif ink_days >= 180:
            hints.append(t("rotation.hint_ink_6m", n=ink_days))
        elif ink_days >= 90:
            hints.append(t("rotation.hint_ink_3m", n=ink_days))
        elif ink_days >= 30:
            hints.append(t("rotation.hint_ink_1m", n=ink_days))
        elif ink_days >= 14:
            hints.append(t("rotation.hint_ink_2w", n=ink_days))
        if color_hint:
            hints.append(color_hint)
        if duplicate_hint:
            hints.append(duplicate_hint)
        hints.extend(clean_hints)
        hints.extend(paper_hints)
        hints.extend(role_hints)
        hints.extend(theme_hints)
        if getattr(ink, "usage_tags", None):
            hints.append(t("rotation.hint_tags_list", tags=getattr(ink, "usage_tags", "")))
        if is_fixed_pairing:
            hints.append(t("rotation.hint_fixed_pair"))
        if getattr(pen, "must_include_in_rotation", False):
            hints.append(t("rotation.hint_must_pen"))
        if has_blocking_rule:
            hints.append(t("rotation.hint_blocking_rule"))
        if auto_decision.enabled:
            hints.append(t("rotation.hint_auto_mode", action=action_label(auto_decision.action), explanation=auto_decision.explanation))
        hints.append(t("rotation.hint_popularity", n=popularity))
        if ink.remaining_ml is not None:
            hints.append(t("rotation.hint_remaining_ml", ml=ink.remaining_ml))
        setup = getattr(pen, "active_nib_setup", None)
        if setup is not None:
            if getattr(setup, "feed_type", None):
                hints.append(t("rotation.hint_feed", feed=setup.feed_type))
            if getattr(setup, "flow_level", None):
                hints.append(t("rotation.hint_setup_flow", n=setup.flow_level))
        if paper is not None:
            hints.append(t("rotation.hint_paper", brand=getattr(paper,"brand",""), name=getattr(paper,"name","")))

        return {
            "pen_id":      pen.id,
            "ink_id":      ink.id,
            "pen_name":    f"{pen.brand} {pen.model}",
            "ink_name":    f"{ink.brand} {ink.name}",
            "fill_system": _fill_system_label(pen.fill_system),
            "color_hex":   ink.color_hex or "#888888",
            "color_family_norm": normalize_color_family(getattr(ink, "color_family", None)) or "",
            "pen_role":    pen_role,
            "theme":       effective_theme,
            "is_must":     bool(getattr(pen, "must_include_in_rotation", False)),
            "is_fixed":    is_fixed_pairing,
            "has_blocked": bool(has_blocking_rule),
            "random_delta": 0,
            "score":       int(score),
            "warnings":    " | ".join(warning_texts + hints) if (warning_texts or hints) else t("rotation.hint_no_problems"),
            "rule_warnings": warning_texts,
            "hints":       hints,
            "empty_bonus":         empty_bonus,
            "pen_days_bonus":     pen_last_used_bonus,
            "ink_days_bonus":     ink_last_used_bonus,
            "ink_days":           ink_days,
            "color_delta": color_delta,
            "rule_delta":  rule_score - 100,
            "clean_delta": clean_delta,
            "paper_delta": paper_delta,
            "role_delta": role_delta,
            "theme_delta": theme_delta,
            "popularity":  popularity_bonus,
            "base_score":  rule_score,
            "duplicate_delta": duplicate_penalty,
            "fixed_bonus": fixed_bonus,
            "must_bonus": must_bonus,
            "auto_action": auto_decision.action,
            "auto_explanation": auto_decision.explanation,
        }

    def _rotation_randomness_percent(self, session) -> int:
        """Setting ``rotation_randomness_percent`` robust als 0–100 lesen."""
        try:
            raw = AppSettings.get(session, "rotation_randomness_percent", "0") or "0"
            return max(0, min(100, int(float(str(raw).replace(",", ".")))))
        except Exception:
            return 0

    def _apply_randomness(self, combos: List[Dict[str, Any]], randomness_percent: int) -> List[Dict[str, Any]]:
        """Mischt deterministisches Scoring mit kontrolliertem Zufall (0–100 %).

        Merge beider 0.2.79-Zweige:
        - 0 % = normale Engine (diese Methode wird dann gar nicht aufgerufen).
        - 100 % = Score besteht praktisch nur noch aus dem Jitter; die Auswahl
          ist damit echt zufällig unter den sicheren Kandidaten.
        - Sicherheitsfilter: Kombinationen mit blockierender harter Regel oder
          Full-Auto-Reject fliegen raus – der Zufall darf alles, außer dem
          Füller schaden. Feste Paarungen 💍 sind davon ausgenommen
          (Override-Prinzip: der Nutzer hat entschieden).
        - Fixe Paarungen und Pflicht-Füller brauchen hier keine Boni: Pass 1
          von :meth:`_build_suggestion_set` garantiert sie strukturell,
          unabhängig vom gejitterten Score.
        """
        rng = random.SystemRandom()
        safe: List[Dict[str, Any]] = []
        for combo in combos:
            if not combo.get("is_fixed") and (combo.get("has_blocked") or combo.get("auto_action") == "reject"):
                continue  # füllerschädigend/abgelehnt → auch im Zufall tabu
            c = dict(combo)
            deterministic = int(c.get("score", 0) or 0)
            jitter = rng.randint(-140, 140)
            mixed = deterministic * (100 - randomness_percent) / 100 + jitter * randomness_percent / 100
            c["random_delta"] = int(round(mixed - deterministic))
            c["score"] = int(round(mixed))
            c["random_mode"] = True
            c["random_percent"] = int(randomness_percent)
            hints = list(c.get("hints") or [])
            hints.append(t("rotation.hint_random_mode", pct=randomness_percent))
            c["hints"] = hints
            c["warnings"] = " | ".join(str(x) for x in (c.get("rule_warnings") or []) + hints)
            safe.append(c)
        return safe

    def get_suggestions(
        self,
        n_slots: int = 5,
        paper_id: int | None = None,
        theme: str | None = None,
        *,
        avoid_pairs: set[tuple[int, int]] | None = None,
    ) -> List[Dict[str, Any]]:
        """Befüllvorschläge für leere Füller mit Farbe, Rolle, Thema und Tinten-last-used.

        v0.2.80 (Merge beider 0.2.79-Zweige):
        - ``avoid_pairs``: (Füller, Tinte)-Paare aus früheren Vorschlagsrunden
          werden hart ausgeschlossen – erneutes Klicken auf "Vorschläge" zeigt
          garantiert andere Tinten. Paar- statt Tinten-Sperre: dieselbe Tinte
          bleibt für andere Füller verfügbar. Feste Paarungen sind ausgenommen.
          Sind alle Kandidaten eines Füllers verbraucht, startet für genau
          diesen Füller automatisch eine neue Runde (🔁) statt Leerlauf.
        - Setting ``rotation_randomness_percent`` (0–100): mischt Zufall in die
          Bewertung; 100 % ist echter Zufall unter den sicheren Kandidaten.
          Blockierende harte Regeln und Auto-Rejects bleiben in jedem Fall
          draußen; 💍/⭐ werden über Pass 1 der Auswahl strukturell garantiert.
        """
        session = get_session()
        combos: List[Dict[str, Any]] = []
        avoid = set(avoid_pairs or ())
        try:
            pens = session.query(Pen).filter_by(is_active=True).all()
            inks = session.query(Ink).filter_by(is_empty=False, is_archived=False).all()
            paper = self._load_paper(session, paper_id)
            active_ink_ids, active_color_families, active_color_hexes = self._active_rotation_context(session)
            _role_configs = load_role_configs(session)   # benutzeranpassbar
            _theme_configs = load_theme_configs(session)  # benutzeranpassbar
            allow_active_duplicates = str(AppSettings.get(session, "rotation_allow_active_ink_duplicates", "0") or "0").strip().lower() in {"1", "true", "yes", "ja"}

            for pen in pens:
                blocked_status = getattr(pen, "availability_status", "available") in BLOCKING_STATUSES
                if getattr(pen, "rotation_blocked", False) or blocked_status:
                    continue
                if pen.current_ink_load:
                    continue

                candidate_inks = list(inks)
                if pen.fixed_ink_id:
                    fixed = session.get(Ink, pen.fixed_ink_id)
                    if fixed and not fixed.is_empty and not fixed.is_archived:
                        candidate_inks = [fixed] + [i for i in candidate_inks if i.id != fixed.id]

                def _base_pool(
                    respect_avoid: bool,
                    *,
                    candidate_inks=candidate_inks,
                    pen=pen,
                ) -> list:
                    pool = []
                    for ink in candidate_inks:
                        # Exakte aktive Tinten nicht erneut vorschlagen. Farb-Doppelungen
                        # bleiben über den Farbfamilien-Malus optional/übersteuerbar;
                        # dieselbe Flasche in zwei Füllern ist dagegen ein Sammler-/
                        # Verbrauchsrisiko und nur per Setting oder fester Paarung sinnvoll.
                        if ink.id in active_ink_ids and pen.fixed_ink_id != ink.id and not allow_active_duplicates:
                            continue
                        # Reroll: bereits vorgeschlagene Paare meiden –
                        # feste Paarungen sind davon ausgenommen.
                        if respect_avoid and (pen.id, ink.id) in avoid and pen.fixed_ink_id != ink.id:
                            continue
                        pool.append(ink)
                    return pool

                pen_pool = _base_pool(respect_avoid=True)
                repeat_round = False
                if not pen_pool and avoid:
                    # Alle Kandidaten dieses Füllers wurden schon vorgeschlagen:
                    # neue Runde für diesen Füller (Wiederholung erlauben).
                    pen_pool = _base_pool(respect_avoid=False)
                    repeat_round = True

                for ink in pen_pool:
                    combo = self._score_pen_ink(
                        pen,
                        ink,
                        session,
                        active_ink_ids=active_ink_ids,
                        active_color_families=active_color_families,
                        paper=paper,
                        theme=theme,
                        role_configs=_role_configs,
                        theme_configs=_theme_configs,
                        empty_bonus=120,
                    )
                    if repeat_round:
                        combo["repeat_round"] = True
                        hints = [t("rotation.hint_repeat_round")] + list(combo.get("hints", []))
                        combo["hints"] = hints
                        combo["warnings"] = " | ".join(str(x) for x in (combo.get("rule_warnings") or []) + hints)
                    combos.append(combo)

            randomness = self._rotation_randomness_percent(session)
            if randomness > 0:
                combos = self._apply_randomness(combos, randomness)
            return self._build_suggestion_set(combos, n_slots, list(active_color_hexes))
        finally:
            session.close()

    def get_refill_recommendations_for_pen(
        self,
        pen_id: int,
        *,
        exclude_ink_id: int | None = None,
        paper_id: int | None = None,
        theme: str | None = None,
        limit: int | None = None,
    ) -> List[Dict[str, Any]]:
        """Empfohlene neue Tinten für einen bereits befüllten Füller.

        Wird von „Leeren + Befüllen“ benutzt. Wichtig: die Liste ist nach derselben
        Engine sortiert wie die normalen Vorschläge und wählt damit Rolle/Thema,
        Farbe und Tinten-last-used vor statt alphabetisch zu sein.
        """
        session = get_session()
        try:
            pen = session.get(Pen, pen_id)
            if not pen:
                return []
            paper = self._load_paper(session, paper_id)
            active_ink_ids, active_color_families, active_hexes = self._active_rotation_context(session, exclude_pen_id=pen_id)
            role_configs = load_role_configs(session)    # benutzerdefinierte Rollen-Regeln auch bei Clean+Refill
            theme_configs = load_theme_configs(session)  # benutzerdefinierte Themen-Regeln auch bei Clean+Refill
            inks = session.query(Ink).filter_by(is_empty=False, is_archived=False).all()
            combos: List[Dict[str, Any]] = []
            for ink in inks:
                if exclude_ink_id is not None and ink.id == exclude_ink_id:
                    continue
                combos.append(self._score_pen_ink(
                    pen,
                    ink,
                    session,
                    active_ink_ids=active_ink_ids,
                    active_color_families=active_color_families,
                    paper=paper,
                    theme=theme,
                    empty_bonus=0,
                    current_ink_id=exclude_ink_id,
                    clean_refill=True,
                    role_configs=role_configs,
                    theme_configs=theme_configs,
                ))
            combos.sort(key=lambda x: x.get("score", 0), reverse=True)
            if limit is not None:
                combos = combos[:limit]
            return combos
        finally:
            session.close()

    # ------------------------------------------------------------------ #
    # Set-Level-Auswahl: Farb-Diversität über alle Vorschläge hinweg      #
    # ------------------------------------------------------------------ #
    def _build_suggestion_set(
        self,
        combos: List[Dict[str, Any]],
        n_slots: int,
        active_hexes: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Wählt aus allen (Füller × Tinte)-Kombinationen eine diverse Menge aus.

        Algorithmus:
        1. Sortiere alle Combos nach Score (hoch → niedrig).
        2. Pass 1 – Pflicht-Füller (must) und feste Paarungen zuerst.
        3. Pass 2 – Restliche leere Füller: wähle pro Füller die Tinte,
           die den besten effektiven Score hat.  Der effektive Score berücksichtigt
           die Farb-Distanz zu allen bereits ausgewählten Tinten, damit das
           Gesamtbild farblich möglichst vielfältig wird.
        4. Jeder Füller erscheint max. 1× im Ergebnis.
        5. Jede Tinte erscheint max. 1× im Ergebnis.

        Zufall (``rotation_randomness_percent``) wirkt bereits vorher über
        :meth:`_apply_randomness` auf die Scores; die Auswahl hier bleibt
        identisch und garantiert 💍/⭐ strukturell in Pass 1.
        """
        # Für jeden Füller: alle Kandidaten nach Score sortiert
        from collections import defaultdict
        pen_candidates: dict = defaultdict(list)
        for c in sorted(combos, key=lambda x: x["score"], reverse=True):
            pen_candidates[c["pen_id"]].append(c)

        selected: List[Dict[str, Any]] = []
        used_ink_ids: set = set()
        selected_hexes: list = list(active_hexes)
        selected_families: set = set()

        def _pick_best_ink(candidates, used_ink_ids, selected_hexes, selected_families):
            """Wählt die Tinte mit dem höchsten effektiven Score für diesen Füller."""
            best_combo = None
            best_eff   = -99999
            for c in candidates:
                if c["ink_id"] in used_ink_ids:
                    continue
                hex_val = c.get("color_hex", "#888888")
                fam     = c.get("color_family_norm", "")
                # Farb-Distanz-Bonus: maximiert Abstand zu allen bisherigen Farben
                if selected_hexes:
                    min_dist = min(_color_distance(hex_val, h) for h in selected_hexes)
                    # 0–441 → 0–30 Punkte Bonus
                    diversity_bonus = min(30, int(min_dist / 12))
                else:
                    diversity_bonus = 30
                # In-Batch-Familien-Malus (zusätzlich zum bereits codierten active-Malus)
                family_penalty = -30 if (fam and fam in selected_families) else 0
                eff = c["score"] + diversity_bonus + family_penalty
                if eff > best_eff:
                    best_eff   = eff
                    best_combo = {**c, "effective_score": eff,
                                  "diversity_bonus": diversity_bonus,
                                  "family_penalty": family_penalty}
            return best_combo

        # ── Pass 1: Pflicht-Füller und feste Paarungen ──────────────────────
        # Über ALLE Kandidaten prüfen (nicht nur den Top-Score): is_fixed ist
        # pro (Füller,Tinte) und liegt evtl. nicht auf Platz 1.
        priority_ids = [
            pid for pid, cands in pen_candidates.items()
            if cands and any(c.get("is_must") or c.get("is_fixed") for c in cands)
        ]
        for pid in priority_ids:
            if len(selected) >= n_slots:
                break
            # Feste Paarung soll nicht nur den Füller priorisieren, sondern wirklich
            # die feste Tinte bevorzugen – selbst wenn eine andere Tinte durch
            # Farbdiversität/Score knapp höher läge.
            cands = pen_candidates[pid]
            fixed_cands = [c for c in cands if c.get("is_fixed")]
            best = _pick_best_ink(fixed_cands or cands, used_ink_ids, selected_hexes, selected_families)
            if best:
                selected.append(best)
                used_ink_ids.add(best["ink_id"])
                selected_hexes.append(best.get("color_hex", "#888888"))
                if best.get("color_family_norm"):
                    selected_families.add(best["color_family_norm"])

        # ── Pass 2: Restliche Füller (nach bestem Roh-Score sortiert) ───────
        remaining_pids = sorted(
            [pid for pid in pen_candidates if pid not in {s["pen_id"] for s in selected}],
            key=lambda pid: pen_candidates[pid][0]["score"] if pen_candidates[pid] else 0,
            reverse=True,
        )
        for pid in remaining_pids:
            if len(selected) >= n_slots:
                break
            best = _pick_best_ink(pen_candidates[pid], used_ink_ids, selected_hexes, selected_families)
            if best:
                selected.append(best)
                used_ink_ids.add(best["ink_id"])
                selected_hexes.append(best.get("color_hex", "#888888"))
                if best.get("color_family_norm"):
                    selected_families.add(best["color_family_norm"])

        # Ergebnis nach effektivem Score sortieren
        return sorted(selected, key=lambda x: x.get("effective_score", x["score"]), reverse=True)

    # ------------------------------------------------------------------ #
    # Aktuelle Rotation (befüllte Füller)                                 #
    # ------------------------------------------------------------------ #
    def get_current_rotation(self) -> List[Dict[str, Any]]:
        session = get_session()
        result: List[Dict[str, Any]] = []
        try:
            for pen in session.query(Pen).filter_by(is_active=True).all():
                # Aktuelle Belegung muss auch Service-/Problemfüller zeigen.
                # Nur Vorschläge zum NEU-Befüllen filtern BLOCKING_STATUSES heraus.
                load = pen.current_ink_load
                if not load:
                    continue
                ink = session.get(Ink, load.ink_id)
                if not ink:
                    continue

                # Violations einmal berechnen; Score nutzt dieselben
                violations = self.rule_engine.check(pen, ink, session)
                max_days   = self.rule_engine.max_days_for(pen, ink, session)
                score      = self.rule_engine.score(pen, ink, violations, session)

                result.append({
                    "pen_id":      pen.id,
                    "ink_id":      ink.id,
                    "load_id":     load.id,
                    "pen_name":    f"{pen.brand} {pen.model}",
                    "ink_name":    f"{ink.brand} {ink.name}",
                    "fill_system": _fill_system_label(pen.fill_system),
                    "color_hex":   ink.color_hex or "#888888",
                    "days":        load.days_loaded,
                    "max_days":    max_days,
                    "score":       score,
                    "overdue":     load.days_loaded > max_days,
                    "popularity":  pen.popularity_rating or 3,
                    "must":        pen.must_include_in_rotation,
                    "fixed":       pen.fixed_ink_id == ink.id,
                    "availability_status": getattr(pen, "availability_status", "available") or "available",
                    "rotation_blocked": bool(getattr(pen, "rotation_blocked", False)),
                })
            return result
        finally:
            session.close()

    # ------------------------------------------------------------------ #
    # Welche befüllten Füller sollte man leeren?                          #
    # ------------------------------------------------------------------ #
    def get_empty_candidates_to_clean(self, n_slots: int = 5) -> List[Dict[str, Any]]:
        """Hohe Standzeit + niedrige Beliebtheit zuerst leeren.

        Die Zeilen enthalten bewusst pen_id/ink_id, damit die UI direkt
        in derselben Zeile Aktionen anbieten kann: reinigen oder reinigen
        und mit einer ausgewählten Tinte neu befüllen.
        """
        current = self.get_current_rotation()
        for r in current:
            r["clean_score"] = (
                r["days"]
                + (50 if r["overdue"] else 0)
                - (r["popularity"] * 8)
                - (80 if r["must"] else 0)
                - (25 if r["fixed"] else 0)
            )
            parts = []
            if r["overdue"]:                            parts.append(t("rotation.clean_reason_overdue"))
            if not r["must"] and r["popularity"] <= 2:  parts.append(t("rotation.clean_reason_low_popularity"))
            if r["fixed"]:                              parts.append(t("rotation.clean_reason_fixed_pair_keep"))
            r["reason"] = ", ".join(parts) if parts else t("rotation.clean_reason_rotatable")

        current.sort(key=lambda x: x["clean_score"], reverse=True)
        return current[:n_slots]



    # ------------------------------------------------------------------ #
    # Freie Tinten im Rotationsbild                                       #
    # ------------------------------------------------------------------ #
    def get_free_inks(self) -> List[Dict[str, Any]]:
        """Tinten, die verfügbar sind und aktuell in keinem Füller stecken."""
        session = get_session()
        try:
            active_ids = {
                load.ink_id
                for load in session.query(InkLoad).filter(InkLoad.cleaned_date.is_(None)).all()
            }
            inks = (
                session.query(Ink)
                .filter_by(is_empty=False, is_archived=False)
                .order_by(Ink.brand, Ink.name)
                .all()
            )
            result = []
            for ink in inks:
                if ink.id in active_ids:
                    continue
                loads = list(getattr(ink, "ink_loads", []) or [])
                last = max((l.loaded_date for l in loads if l.loaded_date), default=None)
                result.append({
                    "ink_id": ink.id,
                    "name": f"{ink.brand} {ink.name}",
                    "color_family": ink.color_family or "—",
                    "color_hex": ink.color_hex or "#888888",
                    "remaining_ml": ink.remaining_ml,
                    "last_loaded": format_date(last) if last else "—",
                    "safety": t(
                        "rotation.free_ink_safety",
                        cleaning=getattr(ink, "cleaning_effort", 3) or 3,
                        feathering=getattr(ink, "feathering_level", 2) or 2,
                    ),
                })
            return result
        finally:
            session.close()

    # ------------------------------------------------------------------ #
    # Verfügbare Tinten für manuelle Befüllung                            #
    # ------------------------------------------------------------------ #
    def get_available_inks(self) -> List[Dict[str, Any]]:
        """Alle nicht leeren/nicht archivierten Tinten für Dropdowns."""
        session = get_session()
        try:
            inks = (
                session.query(Ink)
                .filter_by(is_empty=False, is_archived=False)
                .order_by(Ink.brand, Ink.name)
                .all()
            )
            return [
                {
                    "ink_id": ink.id,
                    "name": f"{ink.brand} {ink.name}",
                    "color_hex": ink.color_hex or "#888888",
                    "remaining_ml": ink.remaining_ml,
                }
                for ink in inks
            ]
        finally:
            session.close()

    # ------------------------------------------------------------------ #
    # Befüllten Füller leeren                                              #
    # ------------------------------------------------------------------ #
    def clean_pen(self, pen_id: int):
        session = get_session()
        try:
            pen = session.get(Pen, pen_id)
            if not pen:
                return False, t("rotation.msg_pen_not_found")

            closed = 0
            for load in pen.ink_loads:
                if load.cleaned_date is None:
                    load.cleaned_date = datetime.now()
                    load.notes = (load.notes or "") + "\n" + t("rotation.note_cleaned_via_rotation")
                    closed += 1

            if closed == 0:
                return False, t("rotation.msg_pen_empty_already")

            session.commit()
            AppEventBus.instance().pens_changed.emit()
            return True, t("rotation.msg_pen_cleaned", pen=f"{pen.brand} {pen.model}")
        except Exception as e:
            session.rollback()
            return False, str(e)
        finally:
            session.close()

    # ------------------------------------------------------------------ #
    # Zentrale Befüll-Logik                                                #
    # ------------------------------------------------------------------ #
    def fill_pen(
        self,
        pen_id: int,
        ink_id: int,
        *,
        override_reason: str = "",
        source: str = "manual",
        notes: str | None = None,
        volume_ml: float | None = None,
        fixed_pairing: bool | None = None,
        close_open_loads: bool = True,
    ):
        """Zentrale Befüllmethode für UI und Rotation.

        Alle Pfade laufen hier durch: manuelles Einfüllen, Vorschlag übernehmen,
        Leeren+Befüllen. Dadurch gelten harte Regeln, Auto-Entscheidung,
        Verbrauchsbuchung und OverrideLog überall identisch.
        """
        session = get_session()
        try:
            pen = session.get(Pen, pen_id)
            ink = session.get(Ink, ink_id)
            if not pen or not ink:
                return False, t("rotation.msg_pen_ink_not_found")
            if ink.is_empty or ink.is_archived:
                return False, t("rotation.msg_ink_empty_archived")
            if getattr(pen, "rotation_blocked", False) or getattr(pen, "availability_status", "available") in BLOCKING_STATUSES:
                return False, t("rotation.msg_pen_blocked")

            violations = self.rule_engine.check(pen, ink, session)
            score_snapshot = self.rule_engine.score(pen, ink, violations, session)
            auto_decision = AutoModeService.decide(session, pen, ink, violations, score_snapshot)
            has_blocking = self.rule_engine.has_blocking_violation(violations)

            if auto_decision.enabled and auto_decision.action == "reject" and not override_reason:
                AutoModeService.log_decision(session, auto_decision.blocking_rule_ids, pen_id, ink_id, auto_decision, t("rotation.note_full_auto_rejected"))
                session.commit()
                return False, auto_decision.explanation
            if has_blocking and not override_reason and not (auto_decision.enabled and auto_decision.action == "allow"):
                return False, t("rotation.msg_hard_rule") + "\n" + self.rule_engine.explain_decision(pen, ink, violations, score_snapshot, session)

            now = datetime.now()
            if close_open_loads:
                for load in pen.ink_loads:
                    if load.cleaned_date is None:
                        load.cleaned_date = now
                        if source == "clean_refill":
                            load.notes = ((load.notes or "") + "\n" + t("rotation.note_cleaned_via_rotation")).strip()

            if fixed_pairing is True:
                pen.fixed_ink_id = ink_id
            is_fixed = bool(fixed_pairing) or (pen.fixed_ink_id == ink_id)

            vol = volume_ml if volume_ml not in (None, 0) else pen.ink_capacity_ml
            if AutoModeService.consumption_tracking_enabled(session) and ink.remaining_ml is not None and vol:
                ink.remaining_ml = apply_ink_consumption(ink.remaining_ml, vol)
                if ink.remaining_ml is not None and ink.remaining_ml <= 0:
                    ink.is_empty = True

            source_notes = {
                "rotation": t("rotation.note_source_rotation"),
                "clean_refill": t("rotation.note_source_clean_refill"),
                "manual": t("rotation.note_source_manual"),
            }
            note_parts = [source_notes.get(source, source)]
            if notes:
                note_parts.append(notes)
            if auto_decision.enabled:
                note_parts.append(auto_decision.explanation)
            session.add(InkLoad(
                pen_id=pen_id,
                ink_id=ink_id,
                loaded_date=now,
                volume_ml=vol,
                is_fixed_pairing=is_fixed,
                notes="\n".join(part for part in note_parts if part),
                override_reasons=override_reason or None,
            ))

            if violations and (override_reason or auto_decision.enabled):
                from database.models import OverrideLog
                explanation = auto_decision.explanation if auto_decision.enabled else self.rule_engine.explain_decision(pen, ink, violations, score_snapshot, session)
                for v in violations:
                    session.add(OverrideLog(
                        rule_id=v.rule_id,
                        pen_id=pen_id,
                        ink_id=ink_id,
                        reason=override_reason or t("rotation.note_full_auto_decision"),
                        decision_mode="full_auto" if auto_decision.enabled else "manual",
                        action=auto_decision.action if auto_decision.enabled else "manual_override",
                        score_snapshot=score_snapshot,
                        explanation=explanation,
                    ))

            session.commit()
            bus = AppEventBus.instance()
            bus.pens_changed.emit()
            bus.inks_changed.emit()
            if source == "rotation":
                return True, t("rotation.msg_fill_success")
            if source == "clean_refill":
                return True, t("rotation.msg_pen_clean_refill_success", pen=f"{pen.brand} {pen.model}", ink=f"{ink.brand} {ink.name}")
            return True, t("rotation.msg_pen_filled_success", pen=f"{pen.brand} {pen.model}", ink=f"{ink.brand} {ink.name}")
        except Exception as e:
            session.rollback()
            return False, str(e)
        finally:
            session.close()

    # ------------------------------------------------------------------ #
    # Befüllten Füller reinigen und direkt neu befüllen                    #
    # ------------------------------------------------------------------ #
    def clean_and_refill(self, pen_id: int, ink_id: int, override_reason: str = ""):
        return self.fill_pen(
            pen_id,
            ink_id,
            override_reason=override_reason,
            source="clean_refill",
            close_open_loads=True,
        )

    # ------------------------------------------------------------------ #
    # Vorschlag übernehmen                                                #
    # ------------------------------------------------------------------ #
    def apply_suggestion(self, pen_id: int, ink_id: int, override_reason: str = ""):
        """Rotationsvorschlag als InkLoad übernehmen."""
        return self.fill_pen(
            pen_id,
            ink_id,
            override_reason=override_reason,
            source="rotation",
            close_open_loads=True,
        )
