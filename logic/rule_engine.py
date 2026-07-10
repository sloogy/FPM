"""
Regel-Engine: prüft und bewertet Füller-Tinten-Kombinationen.
Regeln sind Datenbankeinträge und können im UI aktiviert/deaktiviert und angepasst werden.

FIX v0.2.3:
- check(), score(), max_days_for() akzeptieren nun eine optionale Session.
  So öffnet die RotationEngine keine Zusatz-Sessions mehr, wenn sie die
  Rule-Engine innerhalb ihrer eigenen Session aufruft.
- score() nutzt vorberechnete Violations – Regeln werden pro Kombination
  nur noch einmal aus der DB geladen statt zweimal (check + score).
"""
import logging
import json
from dataclasses import dataclass
from typing import List, Optional

from database.db import get_session
from database.models import Pen, Ink, Rule, AppSettings
from logic.auto_mode_service import AutoModeService, group_label
from i18n.translator import t

_log = logging.getLogger(__name__)


@dataclass
class RuleViolation:
    rule_id: int
    rule_name: str
    description: str
    warn_level: str
    rule_type: str
    can_override: bool = True
    rule_group: str = "rotation"
    auto_action: str = "warn"
    score_delta: int | None = None


LEVEL_COLORS = {"info": "#3498db", "warning": "#f39c12", "critical": "#e67e22", "blocked": "#e74c3c"}
LEVEL_ICONS  = {"info": "ℹ",       "warning": "⚠",        "critical": "🔴",     "blocked": "🚫"}

PENALTY = {"info": 3, "warning": 18, "critical": 35, "blocked": 75}


class RuleEngine:

    def _as_bool(self, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in ("1", "true", "yes", "ja", "y")
        return bool(value)

    def _as_int(self, value, default=0):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _active_nib_setup(self, pen: Pen):
        try:
            return getattr(pen, "active_nib_setup", None)
        except Exception:
            _log.debug("active_nib_setup nicht verfügbar", exc_info=True)
            return None

    def _effective_nib(self, pen: Pen):
        setup = self._active_nib_setup(pen)
        return getattr(setup, "nib", None) or getattr(pen, "nib", None)

    def _effective_stiffness(self, pen: Pen, nib=None) -> int:
        setup = self._active_nib_setup(pen)
        if setup and getattr(setup, "stiffness_feel_level", None):
            return int(setup.stiffness_feel_level)
        nib = nib or self._effective_nib(pen)
        return int(getattr(nib, "stiffness_level", 4) or 4) if nib else 4

    def _nib_text(self, pen: Pen) -> str:
        setup = self._active_nib_setup(pen)
        nib = getattr(setup, "nib", None) or getattr(pen, "nib", None)
        if not nib:
            return ""
        return " ".join([
            getattr(nib, "effective_manufacturer", None) or getattr(nib, "manufacturer", "") or "",
            getattr(nib, "size", "") or "",
            getattr(nib, "effective_physical_size", None) or getattr(nib, "physical_size", "") or "",
            getattr(nib, "grind", "") or "",
            getattr(nib, "material", "") or "",
            getattr(nib, "source", "") or "",
            getattr(nib, "label", "") or "",
            getattr(setup, "feed_type", "") or getattr(nib, "feed_type", "") or "",
            getattr(setup, "feed_notes", "") or getattr(nib, "feed_notes", "") or "",
            getattr(setup, "setup_label", "") or "",
            getattr(setup, "feel_notes", "") or "",
            "flex" if getattr(nib, "is_flexible", False) or self._effective_stiffness(pen, nib) <= 2 else "",
        ]).lower().strip()

    def has_blocking_violation(self, violations: Optional[List[RuleViolation]]) -> bool:
        return any(v.warn_level == "blocked" or v.rule_type == "hard" for v in (violations or []))


    # ------------------------------------------------------------------ #
    # check – Regeln auswerten                                            #
    # ------------------------------------------------------------------ #
    def check(
        self,
        pen: Pen,
        ink: Ink,
        session=None,
    ) -> List[RuleViolation]:
        """Gibt alle ausgelösten Regeln zurück.

        Wird eine Session übergeben, wird sie genutzt (kein close).
        Sonst wird eine eigene Session geöffnet und am Ende geschlossen.
        """
        own_session = session is None
        if own_session:
            session = get_session()
        violations: List[RuleViolation] = []
        try:
            if not AutoModeService.rules_enabled(session):
                return []
            for rule in session.query(Rule).filter_by(is_active=True).all():
                if not AutoModeService.group_enabled(session, getattr(rule, "rule_group", "rotation")):
                    continue
                v = self._evaluate(rule, pen, ink)
                if v:
                    violations.append(v)
        finally:
            if own_session:
                session.close()
        return violations

    # ------------------------------------------------------------------ #
    # score – Bewertung einer Kombination                                 #
    # ------------------------------------------------------------------ #
    def score(
        self,
        pen: Pen,
        ink: Ink,
        violations: Optional[List[RuleViolation]] = None,
        session=None,
    ) -> int:
        """Berechnet den Score einer Füller-Tinten-Kombination.

        Werden bereits berechnete violations übergeben, wird check() NICHT
        nochmals aufgerufen – das vermeidet die doppelte DB-Abfrage.
        """
        if violations is None:
            violations = self.check(pen, ink, session)

        base = 100
        for v in violations:
            if v.score_delta is not None:
                base += int(v.score_delta)
            else:
                base -= PENALTY.get(v.warn_level, 0)

        # Lieblingsfüller bevorzugen
        base += (getattr(pen, "popularity_rating", 3) or 3) * 2
        if getattr(pen, "must_include_in_rotation", False):
            base += 18
        # Feste Tintenpaarung deutlich bevorzugen
        if getattr(pen, "fixed_ink_id", None) == ink.id:
            base += 40

        # Harte/Blockierende Regeln sollen normale Vorschläge praktisch verdrängen.
        # Override bleibt später über die manuelle Befüllung möglich, aber Top-Vorschläge
        # sollen keine riskanten Kombinationen wie Vac + Shimmer priorisieren.
        if self.has_blocking_violation(violations):
            base -= 120

        # Stub/Flex/Italic + Sheen/Shading
        nib = self._effective_nib(pen)
        nib_text = self._nib_text(pen)
        if any(x in nib_text for x in ["stub", "italic", "flex"]):
            if ink.has_sheen:    base += 12
            if ink.has_shading:  base += 8
        if nib and (nib.size or "").upper() == "EF" and (ink.wetness_level or 0) >= 4:
            base += 8

        return max(-100, min(150, base))


    def explain_decision(self, pen: Pen, ink: Ink, violations: Optional[List[RuleViolation]] = None, score: Optional[int] = None, session=None) -> str:
        """Erklärt nachvollziehbar, warum Regeln wirken oder nicht."""
        if violations is None:
            violations = self.check(pen, ink, session)
        if score is None:
            score = self.score(pen, ink, violations, session)
        if not violations:
            return t("rule_engine.no_active_violations", score=score)
        parts = [t("rule_engine.triggered_rules", score=score)]
        for v in violations:
            delta = v.score_delta if v.score_delta is not None else -PENALTY.get(v.warn_level, 0)
            parts.append(t(
                "rule_engine.violation_line",
                level=v.warn_level,
                type=v.rule_type,
                group=group_label(v.rule_group),
                name=v.rule_name,
                description=v.description,
                delta=delta,
            ))
        return "\n".join(parts)

    # ------------------------------------------------------------------ #
    # max_days_for – Reinigungsintervall                                  #
    # ------------------------------------------------------------------ #
    def max_days_for(self, pen: Pen, ink: Ink, session=None) -> int:
        """Standard-Reinigungszeit plus Tinten-Risiko. Tintenwert hat Vorrang."""
        if ink.max_days_in_pen:
            return int(ink.max_days_in_pen)

        own_session = session is None
        if own_session:
            session = get_session()
        try:
            normal  = int(AppSettings.get(session, "cleaning_days_normal",  "28"))
            shimmer = int(AppSettings.get(session, "cleaning_days_shimmer",  "14"))
            pigment = int(AppSettings.get(session, "cleaning_days_pigment",  "10"))
            grail   = int(AppSettings.get(session, "cleaning_days_grail",   "21"))
        finally:
            if own_session:
                session.close()

        days = normal
        if ink.has_shimmer:                    days = min(days, shimmer)
        if ink.is_pigment or ink.is_waterproof: days = min(days, pigment)
        tags = [str(t).lower().strip() for t in (pen.tags_list or [])]
        if "grail" in tags:                    days = min(days, grail)
        return days

    # ------------------------------------------------------------------ #
    # _evaluate – einzelne Regel prüfen                                  #
    # ------------------------------------------------------------------ #
    def _evaluate(self, rule: Rule, pen: Pen, ink: Ink) -> Optional[RuleViolation]:
        try:
            cond = json.loads(rule.condition_data or "{}")
        except json.JSONDecodeError:
            cond = {}

        triggered = False
        ct  = rule.condition_type
        nib = self._effective_nib(pen)
        tags = [t.lower().strip() for t in (pen.tags_list or [])]
        nib_text = self._nib_text(pen)

        if ct == "fill_system_ink_prop":
            triggered = (
                (getattr(pen, "fill_system", None) or "") == cond.get("fill_system")
                and getattr(ink, cond.get("prop", ""), None) == cond.get("value")
            )
        elif ct == "nib_size_wetness":
            expected_size = str(cond.get("nib_size", "")).upper().strip()
            wetness_min = self._as_int(cond.get("wetness_min"), 1)
            has_size = bool(nib and (nib.size or "").upper().strip() == expected_size)
            triggered = has_size and self._as_int(getattr(ink, "wetness_level", None), 3) < wetness_min
        elif ct == "ink_prop_warning":
            prop = cond.get("prop", "")
            expected = cond.get("value")
            triggered = getattr(ink, prop, None) == expected
        elif ct == "pen_tag_ink_prop":
            tag = str(cond.get("tag", "")).lower().strip()
            prop = cond.get("prop", "")
            expected = cond.get("value")
            triggered = tag in tags and getattr(ink, prop, None) == expected
        elif ct == "pen_tag_sheen_cleaning":
            tag = str(cond.get("tag", "")).lower().strip()
            cleaning_min = self._as_int(cond.get("cleaning_min"), 4)
            triggered = tag in tags and bool(getattr(ink, "has_sheen", False)) and self._as_int(getattr(ink, "cleaning_effort", None), 3) >= cleaning_min
        elif ct == "nib_grind_prefers_ink_prop":
            grinds = [str(g).lower() for g in cond.get("grinds", [])]
            props = [str(p) for p in cond.get("props", [])]
            has_target_nib = bool(nib_text) and any(g in nib_text for g in grinds)
            has_prop = any(bool(getattr(ink, p, False)) for p in props)
            triggered = has_target_nib and not has_prop

        if not triggered:
            return None
        return RuleViolation(
            rule.id, rule.name, rule.description or "",
            rule.warn_level, rule.rule_type, True,
            getattr(rule, "rule_group", "rotation") or "rotation",
            getattr(rule, "auto_action", "warn") or "warn",
            getattr(rule, "score_delta", None),
        )
