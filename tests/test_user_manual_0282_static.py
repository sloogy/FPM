"""v0.2.82: Guard – das Benutzerhandbuch bleibt vorhanden, vollständig und wahr.

Kern dieser Guards ist der **Zahlen-Cross-Check**: Das Handbuch nennt bewusst
konkrete Werkswerte (Standzeiten, Score-Gewichte, Schwellen). Ändert jemand
den Code, ohne das Handbuch anzufassen, schlagen diese Tests fehl – Doku-Drift
wird damit zum Testfehler statt zum stillen Fehlerzustand.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs" / "BENUTZERHANDBUCH_DE.md"
MANUALS = {
    "de": MANUAL,
    "en": ROOT / "docs" / "USER_MANUAL_EN.md",
    "fr": ROOT / "docs" / "MANUEL_UTILISATEUR_FR.md",
}


def _manual() -> str:
    return MANUAL.read_text(encoding="utf-8")


def _src(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_manual_exists_and_is_substantial():
    assert MANUAL.exists()
    text = _manual()
    assert len(text) > 20_000, "Handbuch ist als ausführlicher Leitfaden gedacht"
    # Kernkapitel vorhanden
    for heading in (
        "## 1. Grundphilosophie",
        "Datenverzeichnis",
        "## 9. Rotation & Vorschläge im Detail",
        "## 10. Die Regel-Engine",
        "## 12. Ink Safety Timer",
        "Hersteller zuerst",
        "## 22. Fehlerbehebung & FAQ",
        "## 23. Referenz",
        "## 24. Glossar",
    ):
        assert heading in text, f"Kapitel fehlt: {heading}"


def test_manuals_are_linked_from_readme_help_and_packaging():
    readme = _src("README.md")
    spec = _src("FPM.spec")
    expected = {
        "de": "BENUTZERHANDBUCH_DE.md",
        "en": "USER_MANUAL_EN.md",
        "fr": "MANUEL_UTILISATEUR_FR.md",
    }
    assert "help.manual_title" in _src("ui/help_widget.py")
    for lang, filename in expected.items():
        data = json.loads((ROOT / "i18n" / f"{lang}.json").read_text(encoding="utf-8"))
        assert filename in data["help"]["manual_body"]
        assert filename in readme
        assert filename in spec


def test_all_language_manuals_exist_and_cover_current_release():
    minimum_size = {"de": 20_000, "en": 18_000, "fr": 20_000}
    markers = {
        "de": ("Stand: v0.3.05", "## 5. Dashboard", "## 22. Fehlerbehebung"),
        "en": ("Version: v0.3.05", "## 5. Dashboard", "## 22. Troubleshooting"),
        "fr": ("Version : v0.3.05", "## 5. Tableau de bord", "## 22. Dépannage"),
    }
    for lang, manual in MANUALS.items():
        text = manual.read_text(encoding="utf-8")
        assert len(text) >= minimum_size[lang], f"{lang} manual is too thin"
        for marker in markers[lang]:
            assert marker in text, f"{lang}: {marker}"


def test_manual_cleaning_days_match_code_defaults():
    """Die vier Standzeit-Werkswerte im Handbuch == Seeding in database/db.py."""
    db = _src("database/db.py")
    manual = _manual()
    for key, expected in (
        ("cleaning_days_normal", "28"),
        ("cleaning_days_shimmer", "14"),
        ("cleaning_days_pigment", "10"),
        ("cleaning_days_grail", "21"),
    ):
        m = re.search(rf'"{key}":\s*"(\d+)"', db)
        assert m, f"{key} nicht im Seeding gefunden"
        code_val = m.group(1)
        assert code_val == expected, f"Code-Default {key}={code_val} – Test/Handbuch anpassen"
        assert f"`{key}`" in manual and f"**{expected}**" in manual


def test_manual_score_weights_match_engine():
    """Kern-Gewichte im Handbuch == logic/rotation_engine.py."""
    eng = _src("logic/rotation_engine.py")
    manual = _manual()

    # Leer-Bonus 120
    assert "empty_bonus: int = 120" in eng
    assert "+120" in manual

    # Füller-Standzeit: Tage/2, Deckel 80
    assert "min(80, int(last_days / 2))" in eng
    assert "+0…+80" in manual and "÷ 2" in manual

    # Tinten-Standzeit-Staffel
    for pair in (("999", "90"), ("180", "75"), ("90", "50"), ("30", "25"), ("14", "10")):
        days, bonus = pair
        assert re.search(rf"ink_days >= {days}:\s*\n\s*return {bonus}", eng), pair
    assert "0/10/25/50/75/90" in manual

    # Farbfamilie +14 / −18
    assert "return -18," in eng and "return 14," in eng
    assert "+14 / −18" in manual

    # Duplikat-Malus −22
    assert "duplicate_penalty = -22" in eng
    assert "−22" in manual

    # Blockade-Deckel −50, Reject −999
    assert "min(score, -50)" in eng and "min(score, -999)" in eng
    assert "−50" in manual and "−999" in manual

    # Jitter ±140 und Mischformel
    assert "rng.randint(-140, 140)" in eng
    assert "±140" in manual and "(100−p)/100" in manual


def test_manual_selection_layer_matches_engine():
    """Diversitätsbonus 0–30 und Batch-Familien-Malus −30 stimmen mit der Auswahl überein."""
    eng = _src("logic/rotation_engine.py")
    manual = _manual()
    assert re.search(r"min\(30,", eng), "Diversitätsbonus-Deckel 30 nicht gefunden"
    assert "-30" in eng
    assert "0–30" in manual and "− 30" in manual


def test_manual_timer_threshold_and_early_stop_match_code():
    manual = _manual()
    # v0.3.05: 80%-Schwelle wanderte in den Qt-freien logic.dashboard_service.
    assert 'soon_ratio * r["max"]' in _src("logic/dashboard_service.py")
    assert "TIMER_SOON_RATIO = 0.8" in _src("logic/dashboard_service.py")
    assert "80 %" in manual
    assert "confidence >= 0.65" in _src("logic/pen_dimensions_service.py")
    assert "0.65" in manual


def test_manual_default_rules_match_seeding():
    """Alle 8 Standard-Regelnamen aus db.py stehen wörtlich im Handbuch."""
    db = _src("database/db.py")
    manual = _manual()
    # Kontextgenau: nur Namen unmittelbar in Rule(...)-Blöcken (nicht Ink-Seeds).
    rule_names = re.findall(r'Rule\(\s*\n\s*name="([^"]+)"', db)
    assert len(rule_names) == 8, rule_names
    for name in rule_names:
        assert name in manual, f"Standardregel fehlt im Handbuch: {name}"


def test_manual_roles_match_role_config():
    src = _src("logic/role_config.py")
    manual = _manual()
    block = src[src.index("DEFAULT_ROLE_CONFIGS"):src.index("DEFAULT_THEME_CONFIGS")]
    roles = re.findall(r'^    "(\w+)": \{', block, re.M)
    assert len(roles) == 13, roles
    for role in roles:
        assert role in manual, f"Rolle fehlt im Handbuch: {role}"


def test_manual_data_files_match_code():
    manual = _manual()
    assert "pen_dimensions_cache.json" in _src("logic/pen_dimensions_service.py")
    assert "pen_dimensions_cache.json" in manual
    assert "manufacturer_domains.json" in manual
    assert "FPM_DATA_DIR" in _src("database/db.py") and "FPM_DATA_DIR" in manual


def test_manual_settings_reference_matches_seeding():
    """Referenztabelle 23.1: Schlüssel existieren im Seeding mit dem genannten Werkswert."""
    db = _src("database/db.py")
    manual = _manual()
    for key, default in (
        ("rotation_randomness_percent", "0"),
        ("rotation_allow_active_ink_duplicates", "0"),
        ("rules_enabled", "1"),
        ("full_auto_mode", "0"),
        ("full_auto_can_reject", "1"),
        ("full_auto_can_override", "0"),
        ("full_auto_logging", "1"),
        ("rule_group_consumption_enabled", "0"),
    ):
        assert f'"{key}": "{default}"' in db, f"Seeding-Drift: {key}"
        assert f"`{key}`" in manual, f"Referenztabelle unvollständig: {key}"
