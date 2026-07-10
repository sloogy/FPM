"""
Rollen-Konfiguration für die intelligente Rotation.

Jede Rotationsrolle hat bearbeitbare Präferenzen:
- Tinten-Eigenschaften (Nässe, Reinigung, Shimmer, Pigment, Sheen)
- Bevorzugte Tinten-Tags (usage_tags)
- Typische Federgrössen (z.B. EF, F) und Füllsysteme
- Score-Bonus/Malus bei Übereinstimmung

Gespeichert in AppSettings als JSON (Schlüssel: 'rotation_role_configs').
Engine liest daraus; fällt auf Defaults zurück wenn kein Eintrag vorhanden.
"""
from __future__ import annotations
import json
import logging
from typing import Any

from i18n.translator import t

# DB-Importe sind LAZY (in den load/save-Funktionen), damit das reine
# Tinten-Scoring ohne Datenbank-/SQLAlchemy-Abhängigkeit nutzbar/testbar ist.

_log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Federgrössen-Kategorien (für UI-Checkboxes und Scoring)
# ─────────────────────────────────────────────────────────────────────────────

NIB_SIZE_CATEGORIES = [
    ("ef",   "EF / XXF"),
    ("f",    "F"),
    ("m",    "M"),
    ("b",    "B"),
    ("stub", "Stub / Italic"),
    ("flex", "Flex"),
    ("ci",   "CI / Oblique"),
]

# Ink-Präferenzen pro Nib-Kategorie  (None = keine Vorgabe)
NIB_SIZE_INK_PREFS: dict[str, dict] = {
    "ef":   {"min_wetness": 3, "pigment_penalty": -18, "dry_penalty": -18, "wet_bonus": 12},
    "f":    {"min_wetness": 2, "pigment_penalty": -12, "dry_penalty": -10, "wet_bonus":  8},
    "m":    {},   # neutral
    "b":    {"sheen_bonus": 10, "shimmer_bonus": 8,  "shading_bonus": 6},
    "stub": {"sheen_bonus": 10, "shading_bonus": 10, "shimmer_bonus": 6},
    "flex": {"min_wetness": 4, "pigment_penalty": -20, "dry_penalty": -20, "wet_bonus": 15},
    "ci":   {"min_wetness": 2, "dry_penalty": -8,    "wet_bonus": 5},
}


def categorize_nib_size(nib_size: str) -> str | None:
    """Ordnet eine Federgrössen-Beschriftung einer Scoring-Kategorie zu.

    Reihenfolge ist wichtig: Schliff-Schlüsselwörter (Stub/Italic/Flex/CI)
    werden VOR der numerischen Breiten-Erkennung geprüft, damit z.B.
    "1.5 Stub" als 'stub' und nicht als 'b' (Breite) klassifiziert wird.
    """
    if not nib_size:
        return None
    s = nib_size.upper().strip()
    # 1) Schliff-Schlüsselwörter zuerst
    if "STUB" in s or "ITALIC" in s or "CURSIVE" in s:
        return "stub"
    if "FLEX" in s:
        return "flex"
    if "OBLIQUE" in s or s == "CI" or "CURSIVE ITALIC" in s:
        return "ci"
    # 2) Standardgrössen
    if s in {"EF", "XXF", "UEF", "XXXF", "XF", "EXXXF"}:
        return "ef"
    if s in {"F", "SF", "FEF"}:
        return "f"
    if s in {"M", "MS", "SM", "MF", "FM"}:
        return "m"
    # 3) Breite Federn / numerische Strichbreiten (nur wenn kein Schliff-Keyword)
    if s in {"B", "BB", "BBB", "SB", "BS", "2B", "3B"} or s.startswith(("1.", "1,", "2.", "2,")):
        return "b"
    return None   # unbekannt / nicht kategorisierbar


# ─────────────────────────────────────────────────────────────────────────────
# Default-Konfiguration (spiegelt die bisherigen Hardcode-Werte wider)
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_ROLE_CONFIGS: dict[str, dict[str, Any]] = {
    "writer": {
        "min_wetness": 2, "max_wetness": 5,
        "max_cleaning": 4,
        "allow_shimmer": None, "allow_pigment": None,
        "prefer_sheen": False, "prefer_shading": False,
        "target_tags": ["edc", "journal", "work"],
        "preferred_nib_sizes": [],
        "preferred_fill_systems": [],
        "score_match": 10, "score_miss": -5,
    },
    "edc": {
        "min_wetness": 2, "max_wetness": 5,
        "max_cleaning": 3,
        "allow_shimmer": False, "allow_pigment": False,
        "prefer_sheen": False, "prefer_shading": False,
        "target_tags": ["edc", "work", "business", "fine_nib", "cheap_paper", "document"],
        "preferred_nib_sizes": ["ef", "f"],
        "preferred_fill_systems": ["piston", "converter", "cartridge"],
        "score_match": 15, "score_miss": -10,
    },
    "agenda": {
        "min_wetness": 1, "max_wetness": 4,
        "max_cleaning": 3,
        "allow_shimmer": False, "allow_pigment": False,
        "prefer_sheen": False, "prefer_shading": False,
        "target_tags": ["agenda", "edc", "fine_nib", "cheap_paper", "document"],
        "preferred_nib_sizes": ["ef", "f"],
        "preferred_fill_systems": [],
        "score_match": 15, "score_miss": -12,
    },
    "journal": {
        "min_wetness": 2, "max_wetness": 5,
        "max_cleaning": 4,
        "allow_shimmer": None, "allow_pigment": None,
        "prefer_sheen": True, "prefer_shading": True,
        "target_tags": ["journal", "creative", "shading"],
        "preferred_nib_sizes": [],
        "preferred_fill_systems": [],
        "score_match": 14, "score_miss": -8,
    },
    "work": {
        "min_wetness": 2, "max_wetness": 4,
        "max_cleaning": 3,
        "allow_shimmer": False, "allow_pigment": False,
        "prefer_sheen": False, "prefer_shading": False,
        "target_tags": ["work", "business", "document", "cheap_paper", "archive"],
        "preferred_nib_sizes": ["ef", "f", "m"],
        "preferred_fill_systems": [],
        "score_match": 14, "score_miss": -10,
    },
    "creative": {
        "min_wetness": 2, "max_wetness": 5,
        "max_cleaning": 5,
        "allow_shimmer": True, "allow_pigment": None,
        "prefer_sheen": True, "prefer_shading": True,
        "target_tags": ["creative", "sheen_showcase", "shading", "broad_nib"],
        "preferred_nib_sizes": ["m", "b", "stub"],
        "preferred_fill_systems": [],
        "score_match": 14, "score_miss": -5,
    },
    "letter": {
        "min_wetness": 2, "max_wetness": 5,
        "max_cleaning": 4,
        "allow_shimmer": None, "allow_pigment": None,
        "prefer_sheen": True, "prefer_shading": True,
        "target_tags": ["letter", "journal", "shading", "sheen_showcase"],
        "preferred_nib_sizes": [],
        "preferred_fill_systems": [],
        "score_match": 12, "score_miss": -5,
    },
    "collector": {
        "min_wetness": 2, "max_wetness": 4,
        "max_cleaning": 2,
        "allow_shimmer": False, "allow_pigment": False,
        "prefer_sheen": False, "prefer_shading": False,
        "target_tags": ["collector_safe", "vintage_safe", "easy_clean", "archive"],
        "preferred_nib_sizes": [],
        "preferred_fill_systems": [],
        "score_match": 14, "score_miss": -25,
    },
    "vintage": {
        "min_wetness": 2, "max_wetness": 4,
        "max_cleaning": 2,
        "allow_shimmer": False, "allow_pigment": False,
        "prefer_sheen": False, "prefer_shading": False,
        "target_tags": ["vintage_safe", "collector_safe", "easy_clean", "archive"],
        "preferred_nib_sizes": [],
        "preferred_fill_systems": ["eyedropper"],
        "score_match": 14, "score_miss": -30,
    },
    "problem": {
        "min_wetness": 3, "max_wetness": 5,
        "max_cleaning": 2,
        "allow_shimmer": False, "allow_pigment": False,
        "prefer_sheen": False, "prefer_shading": False,
        "target_tags": ["easy_clean", "testing", "cheap_paper", "fine_nib"],
        "preferred_nib_sizes": [],
        "preferred_fill_systems": [],
        "score_match": 14, "score_miss": -20,
    },
    "fine": {
        "min_wetness": 3, "max_wetness": 5,
        "max_cleaning": 4,
        "allow_shimmer": None, "allow_pigment": False,
        "prefer_sheen": False, "prefer_shading": False,
        "target_tags": ["fine_nib", "edc", "agenda", "cheap_paper", "document"],
        "preferred_nib_sizes": ["ef", "f"],
        "preferred_fill_systems": [],
        "score_match": 15, "score_miss": -20,
    },
    "broad": {
        "min_wetness": 2, "max_wetness": 5,
        "max_cleaning": 5,
        "allow_shimmer": True, "allow_pigment": None,
        "prefer_sheen": True, "prefer_shading": True,
        "target_tags": ["broad_nib", "creative", "sheen_showcase", "shading"],
        "preferred_nib_sizes": ["b", "stub"],
        "preferred_fill_systems": [],
        "score_match": 12, "score_miss": -5,
    },
    "must": {
        "min_wetness": 2, "max_wetness": 5,
        "max_cleaning": 3,
        "allow_shimmer": None, "allow_pigment": None,
        "prefer_sheen": False, "prefer_shading": False,
        "target_tags": ["edc", "work", "business", "easy_clean", "document"],
        "preferred_nib_sizes": [],
        "preferred_fill_systems": [],
        "score_match": 10, "score_miss": -8,
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Load / Save
# ─────────────────────────────────────────────────────────────────────────────
_SETTINGS_KEY = "rotation_role_configs"


def load_role_configs(session=None) -> dict[str, dict[str, Any]]:
    """Lädt Rollen-Konfiguration aus AppSettings. Fällt auf Defaults zurück."""
    from database.db import get_session
    from database.models import AppSettings
    _own = session is None
    if _own:
        session = get_session()
    try:
        raw = AppSettings.get(session, _SETTINGS_KEY)
        if raw:
            stored: dict = json.loads(raw)
            # Merge with defaults: stored overrides, missing roles get defaults
            merged = {k: dict(v) for k, v in DEFAULT_ROLE_CONFIGS.items()}
            for role, cfg in stored.items():
                if role in merged:
                    merged[role].update(cfg)
                else:
                    merged[role] = cfg   # user-added custom role
            return merged
    except Exception:
        _log.exception("Fehler beim Laden der Rollen-Konfiguration")
    finally:
        if _own:
            session.close()
    return {k: dict(v) for k, v in DEFAULT_ROLE_CONFIGS.items()}


def save_role_configs(configs: dict[str, dict[str, Any]], session=None) -> None:
    """Speichert Rollen-Konfiguration in AppSettings."""
    from database.db import get_session
    from database.models import AppSettings
    _own = session is None
    if _own:
        session = get_session()
    try:
        # AppSettings.set committet bereits intern
        AppSettings.set(session, _SETTINGS_KEY, json.dumps(configs, ensure_ascii=False))
    finally:
        if _own:
            session.close()


def reset_role_configs(session=None) -> None:
    save_role_configs({k: dict(v) for k, v in DEFAULT_ROLE_CONFIGS.items()}, session)


# ─────────────────────────────────────────────────────────────────────────────
# Themen-Konfiguration (parallel zu Rollen, ebenfalls editierbar)
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_THEME_CONFIGS: dict[str, dict[str, Any]] = {
    "edc":        {"min_wetness": 2, "max_wetness": 5, "max_cleaning": 3,
                   "allow_shimmer": False, "allow_pigment": None,
                   "prefer_sheen": False, "prefer_shading": False,
                   "target_tags": ["edc", "work", "business", "fine_nib", "cheap_paper", "document"],
                   "preferred_nib_sizes": [], "preferred_fill_systems": [],
                   "score_match": 14, "score_miss": -10},
    "agenda":     {"min_wetness": 1, "max_wetness": 4, "max_cleaning": 3,
                   "allow_shimmer": False, "allow_pigment": False,
                   "prefer_sheen": False, "prefer_shading": False,
                   "target_tags": ["agenda", "edc", "fine_nib", "cheap_paper", "document"],
                   "preferred_nib_sizes": [], "preferred_fill_systems": [],
                   "score_match": 14, "score_miss": -12},
    "journal":    {"min_wetness": 2, "max_wetness": 5, "max_cleaning": 4,
                   "allow_shimmer": None, "allow_pigment": None,
                   "prefer_sheen": True, "prefer_shading": True,
                   "target_tags": ["journal", "creative", "shading"],
                   "preferred_nib_sizes": [], "preferred_fill_systems": [],
                   "score_match": 14, "score_miss": -8},
    "work":       {"min_wetness": 2, "max_wetness": 4, "max_cleaning": 3,
                   "allow_shimmer": False, "allow_pigment": False,
                   "prefer_sheen": False, "prefer_shading": False,
                   "target_tags": ["work", "business", "document", "cheap_paper", "archive"],
                   "preferred_nib_sizes": [], "preferred_fill_systems": [],
                   "score_match": 14, "score_miss": -10},
    "creative":   {"min_wetness": 2, "max_wetness": 5, "max_cleaning": 5,
                   "allow_shimmer": True, "allow_pigment": None,
                   "prefer_sheen": True, "prefer_shading": True,
                   "target_tags": ["creative", "sheen_showcase", "shading", "broad_nib"],
                   "preferred_nib_sizes": [], "preferred_fill_systems": [],
                   "score_match": 14, "score_miss": -5},
    "letter":     {"min_wetness": 2, "max_wetness": 5, "max_cleaning": 4,
                   "allow_shimmer": None, "allow_pigment": None,
                   "prefer_sheen": True, "prefer_shading": True,
                   "target_tags": ["letter", "journal", "shading", "sheen_showcase"],
                   "preferred_nib_sizes": [], "preferred_fill_systems": [],
                   "score_match": 12, "score_miss": -5},
    "archive":    {"min_wetness": 2, "max_wetness": 4, "max_cleaning": 3,
                   "allow_shimmer": False, "allow_pigment": None,
                   "prefer_sheen": False, "prefer_shading": False,
                   "target_tags": ["archive", "document", "business", "waterproof"],
                   "preferred_nib_sizes": [], "preferred_fill_systems": [],
                   "score_match": 14, "score_miss": -12},
    "cheap_paper":{"min_wetness": 1, "max_wetness": 3, "max_cleaning": 3,
                   "allow_shimmer": False, "allow_pigment": False,
                   "prefer_sheen": False, "prefer_shading": False,
                   "target_tags": ["cheap_paper", "fine_nib", "edc", "business", "document"],
                   "preferred_nib_sizes": ["ef", "f"], "preferred_fill_systems": [],
                   "score_match": 14, "score_miss": -12},
    "fine_nib":   {"min_wetness": 3, "max_wetness": 5, "max_cleaning": 4,
                   "allow_shimmer": False, "allow_pigment": False,
                   "prefer_sheen": False, "prefer_shading": False,
                   "target_tags": ["fine_nib", "agenda", "edc", "cheap_paper", "document"],
                   "preferred_nib_sizes": ["ef", "f"], "preferred_fill_systems": [],
                   "score_match": 14, "score_miss": -15},
    "broad_nib":  {"min_wetness": 2, "max_wetness": 5, "max_cleaning": 5,
                   "allow_shimmer": True, "allow_pigment": None,
                   "prefer_sheen": True, "prefer_shading": True,
                   "target_tags": ["broad_nib", "creative", "sheen_showcase", "shading"],
                   "preferred_nib_sizes": ["b", "stub"], "preferred_fill_systems": [],
                   "score_match": 12, "score_miss": -5},
    "sheen_showcase": {"min_wetness": 3, "max_wetness": 5, "max_cleaning": 5,
                   "allow_shimmer": None, "allow_pigment": None,
                   "prefer_sheen": True, "prefer_shading": False,
                   "target_tags": ["sheen_showcase", "creative", "broad_nib"],
                   "preferred_nib_sizes": ["b", "stub"], "preferred_fill_systems": [],
                   "score_match": 16, "score_miss": -8},
    "testing":    {"min_wetness": 1, "max_wetness": 5, "max_cleaning": 5,
                   "allow_shimmer": None, "allow_pigment": None,
                   "prefer_sheen": False, "prefer_shading": False,
                   "target_tags": ["testing", "creative", "easy_clean"],
                   "preferred_nib_sizes": [], "preferred_fill_systems": [],
                   "score_match": 8, "score_miss": -3},
}

_THEME_SETTINGS_KEY = "rotation_theme_configs"


def load_theme_configs(session=None) -> dict[str, dict[str, Any]]:
    from database.db import get_session
    from database.models import AppSettings
    _own = session is None
    if _own:
        session = get_session()
    try:
        raw = AppSettings.get(session, _THEME_SETTINGS_KEY)
        if raw:
            stored = json.loads(raw)
            merged = {k: dict(v) for k, v in DEFAULT_THEME_CONFIGS.items()}
            for theme, cfg in stored.items():
                if theme in merged:
                    merged[theme].update(cfg)
                else:
                    merged[theme] = cfg
            return merged
    except Exception:
        _log.exception("Fehler beim Laden der Themen-Konfiguration")
    finally:
        if _own:
            session.close()
    return {k: dict(v) for k, v in DEFAULT_THEME_CONFIGS.items()}


def save_theme_configs(configs: dict[str, dict[str, Any]], session=None) -> None:
    from database.db import get_session
    from database.models import AppSettings
    _own = session is None
    if _own:
        session = get_session()
    try:
        AppSettings.set(session, _THEME_SETTINGS_KEY, json.dumps(configs, ensure_ascii=False))
    finally:
        if _own:
            session.close()


def reset_theme_configs(session=None) -> None:
    save_theme_configs({k: dict(v) for k, v in DEFAULT_THEME_CONFIGS.items()}, session)


def _theme_label_for_hint(theme: str) -> str:
    key = f"rotation.theme_{theme}"
    lbl = t(key)
    return theme if lbl == key else lbl


def score_ink_for_theme(
    theme: str | None,
    ink,
    fill_system: str,
    configs: dict[str, dict[str, Any]] | None = None,
    nib_size: str | None = None,
) -> tuple[int, list[str]]:
    """Score-Modifier einer Tinte für ein Thema (gleicher Kern wie Rollen)."""
    theme = (theme or "").strip().lower()
    if not theme:
        return 0, []
    if configs is None:
        configs = DEFAULT_THEME_CONFIGS
    cfg = configs.get(theme)
    if not cfg:
        return 0, []
    # Wiederverwendung des Rollen-Scorings mit Themen-Label
    return _score_ink_for_config(cfg, ink, fill_system, nib_size, _theme_label_for_hint(theme))


# ─────────────────────────────────────────────────────────────────────────────
# Engine-Helfer – genutzt von rotation_engine._score_pen_ink() via score_ink_for_role/theme
# ─────────────────────────────────────────────────────────────────────────────
def _role_label_for_hint(role: str) -> str:
    """Übersetztes Rollen-Label für Hints (Fallback: roher Code)."""
    key = f"rotation.role_{role}"
    label = t(key)
    return role if label == key else label


def score_ink_for_role(
    role: str,
    ink,
    fill_system: str,
    configs: dict[str, dict[str, Any]] | None = None,
    nib_size: str | None = None,
) -> tuple[int, list[str]]:
    """Berechnet Score-Modifier einer Tinte für eine Rolle."""
    if configs is None:
        configs = DEFAULT_ROLE_CONFIGS
    cfg = configs.get(role) or configs.get("writer") or {}
    return _score_ink_for_config(cfg, ink, fill_system, nib_size, _role_label_for_hint(role))


def _score_ink_for_config(
    cfg: dict[str, Any],
    ink,
    fill_system: str,
    nib_size: str | None,
    rlabel: str,
) -> tuple[int, list[str]]:
    """Gemeinsamer Scoring-Kern für Rollen UND Themen.
    Bewertet eine Tinte gegen eine Konfiguration (Nässe, Reinigung, Shimmer,
    Pigment, Sheen, Shading, Tags, Federgrössen). Verhindert Doppelbestrafung:
    wenn eine konkrete Feder vorliegt, übernimmt der Nib-Block die Physik.
    """
    score = 0
    hints: list[str] = []
    wetness  = getattr(ink, "wetness_level",   3) or 3
    cleaning = getattr(ink, "cleaning_effort", 3) or 3
    shimmer  = bool(getattr(ink, "has_shimmer",   False))
    pigment  = bool(getattr(ink, "is_pigment",    False))
    waterp   = bool(getattr(ink, "is_waterproof", False))
    sheen_lv = getattr(ink, "sheen_level",     0) or 0
    shading  = getattr(ink, "shading_level",   0) or 0
    bonus    = int(cfg.get("score_match", 12))
    penalty  = int(cfg.get("score_miss",  -8))

    # Konkrete Federkategorie des Füllers (falls bekannt)
    actual_nib_cat = categorize_nib_size(nib_size or "") if nib_size else None
    # Wenn eine konkrete Feder vorliegt, übernimmt der Nib-Block die physikalischen
    # Eigenschaften (Nässe, Pigment) — die Rolle prüft diese dann NICHT erneut,
    # um Doppelbestrafung zu vermeiden. (#2)
    nib_handles_physical = actual_nib_cat is not None and bool(NIB_SIZE_INK_PREFS.get(actual_nib_cat))

    # ── Nässe (nur wenn keine konkrete Feder die Physik übernimmt) ──────────
    if not nib_handles_physical:
        min_w = cfg.get("min_wetness"); max_w = cfg.get("max_wetness")
        if min_w and wetness < min_w:
            score += penalty; hints.append(t("rotation.hint_too_dry", role=rlabel, n=min_w))
        elif max_w and wetness > max_w:
            score += penalty // 2; hints.append(t("rotation.hint_too_wet", role=rlabel, n=max_w))
        elif min_w and wetness >= min_w:
            score += bonus // 2

    # ── Reinigung (Use-Case, immer relevant) ───────────────────────────────
    max_c = cfg.get("max_cleaning")
    if max_c and cleaning > max_c:
        score += penalty; hints.append(t("rotation.hint_cleaning_high", role=rlabel, c=cleaning, max=max_c))
    elif max_c and cleaning <= max_c:
        score += bonus // 3

    # ── Shimmer (Use-Case-Effekt, nicht rein physikalisch) ──────────────────
    allow_shimmer = cfg.get("allow_shimmer")
    if shimmer and allow_shimmer is False:
        score += penalty; hints.append(t("rotation.hint_shimmer_avoid", role=rlabel))
    elif shimmer and allow_shimmer is True:
        score += bonus // 2; hints.append(t("rotation.hint_shimmer_ok", role=rlabel))

    # ── Pigment (nur wenn keine konkrete Feder die Physik übernimmt) ────────
    if not nib_handles_physical:
        allow_pigment = cfg.get("allow_pigment")
        if pigment and allow_pigment is False:
            score += penalty; hints.append(t("rotation.hint_pigment_avoid", role=rlabel))
        elif pigment and allow_pigment is True:
            score += bonus // 2

    # ── Sheen bevorzugt ─────────────────────────────────────────────────────
    if cfg.get("prefer_sheen") and sheen_lv >= 3:
        score += bonus // 2; hints.append(t("rotation.hint_sheen_ok", role=rlabel))
    elif cfg.get("prefer_sheen") and sheen_lv == 0:
        score -= 5

    # ── Shading bevorzugt ───────────────────────────────────────────────────
    if cfg.get("prefer_shading") and shading >= 3:
        score += bonus // 3; hints.append(t("rotation.hint_shading_ok", role=rlabel))

    # ── Tinten-Tags ─────────────────────────────────────────────────────────
    target_tags = set(cfg.get("target_tags") or [])
    if target_tags:
        raw_tags = getattr(ink, "usage_tags", None) or ""
        ink_tags = {s.strip().lower() for s in str(raw_tags).split(",") if s.strip()}
        matches  = target_tags & ink_tags
        if matches:
            score += bonus; hints.append(t("rotation.hint_tags_match", role=rlabel, tags=", ".join(sorted(matches))))
        else:
            score += penalty // 2

    # ── Wasserdicht-Sonderfall (config-getrieben statt hartkodierter Code) ──
    _wp_tags = {"archive", "document", "waterproof"}
    if waterp and (_wp_tags & set(cfg.get("target_tags") or [])):
        score += bonus // 3; hints.append(t("rotation.hint_waterproof_ok", role=rlabel))

    # ── Bevorzugte Füllsysteme ──────────────────────────────────────────────
    preferred_fill_systems = {str(v).strip().lower()
                              for v in (cfg.get("preferred_fill_systems") or [])
                              if str(v).strip()}
    actual_fill_system = (fill_system or "").strip().lower()
    if preferred_fill_systems and actual_fill_system:
        if actual_fill_system in preferred_fill_systems:
            score += bonus // 2
            hints.append(t("rotation.hint_fillsys_ok", role=rlabel, sys=actual_fill_system))
        else:
            score += penalty // 2
            hints.append(t("rotation.hint_fillsys_bad", role=rlabel, sys=actual_fill_system))

    # ── Federgrössen-Scoring (physikalische Eigenschaften der Feder) ────────
    preferred_nib_cats = set(cfg.get("preferred_nib_sizes") or [])
    nib_cats_to_score = {actual_nib_cat} if actual_nib_cat else preferred_nib_cats
    for nib_cat in nib_cats_to_score:
        prefs = NIB_SIZE_INK_PREFS.get(nib_cat or "", {})
        if not prefs:
            continue
        nib_label = dict(NIB_SIZE_CATEGORIES).get(nib_cat, nib_cat)
        min_w_nib = prefs.get("min_wetness")
        if min_w_nib and wetness < min_w_nib:
            score += prefs.get("dry_penalty", -10)
            hints.append(t("rotation.hint_nib_dry", nib=nib_label, n=min_w_nib))
        elif prefs.get("wet_bonus") and wetness >= (min_w_nib or 3):
            score += prefs["wet_bonus"]
            hints.append(t("rotation.hint_nib_wet_ok", nib=nib_label))
        if pigment and prefs.get("pigment_penalty"):
            score += prefs["pigment_penalty"]
            hints.append(t("rotation.hint_nib_pigment", nib=nib_label))
        if sheen_lv >= 3 and prefs.get("sheen_bonus"):
            score += prefs["sheen_bonus"]
            hints.append(t("rotation.hint_nib_sheen", nib=nib_label))
        if shimmer and prefs.get("shimmer_bonus"):
            score += prefs["shimmer_bonus"]
            hints.append(t("rotation.hint_nib_shimmer", nib=nib_label))
        if shading >= 3 and prefs.get("shading_bonus"):
            score += prefs["shading_bonus"]
            hints.append(t("rotation.hint_nib_shading", nib=nib_label))

    return score, hints
