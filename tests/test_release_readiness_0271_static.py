"""v0.2.90 release-readiness hardening checks."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_readme_and_windows_docs_are_current_version():
    assert "# FountainPen Manager v0.2.90" in read("README.md")
    for rel in (
        "docs/WINDOWS_RELEASE_DE.md",
        "docs/WINDOWS_RELEASE_EN.md",
        "docs/WINDOWS_RELEASE_FR.md",
    ):
        text = read(rel)
        assert "0.2.90" in text
        assert "0.2.67" not in text
        assert "FPM_DATA_DIR" in text


def test_sidebar_is_grouped_for_dau_navigation():
    src = read("ui/navigation.py")
    assert "GROUPED_ORDER" in src
    for key in (
        "nav.group_start",
        "nav.group_collection",
        "nav.group_usage",
        "nav.group_analysis",
        "nav.group_system",
    ):
        assert key in src
    assert "PAGE_SHORTCUTS" in src
    assert "Alt+5" in src


def test_runtime_i18n_logics_use_translation_keys():
    combined = "\n".join(
        read(rel)
        for rel in (
            "logic/rotation_engine.py",
            "logic/rule_engine.py",
            "logic/auto_mode_service.py",
        )
    )
    forbidden_runtime_fragments = [
        '"Tinte bereits aktiv"',
        '"Reinigung überfällig"',
        '"niedrige Beliebtheit"',
        '"Über Rotationstabelle geleert."',
        '"Full Auto Mode ist ausgeschaltet; Nutzer entscheidet."',
        '"Keine aktiven Regelverletzungen. Score',
        '"Score {score}. Ausgelöste Regeln',
        '"Automatisch abgelehnt"',
    ]
    for needle in forbidden_runtime_fragments:
        assert needle not in combined
    for key in (
        "rotation.ink_already_active",
        "rotation.note_cleaned_via_rotation",
        "rule_engine.no_active_violations",
        "auto_mode.disabled",
    ):
        assert key in combined


def test_gui_smoke_docs_and_script_exist():
    for rel in (
        "docs/GUI_SMOKE_TEST_DE.md",
        "docs/GUI_SMOKE_TEST_EN.md",
        "docs/GUI_SMOKE_TEST_FR.md",
    ):
        text = read(rel)
        assert "tools/gui_smoke_test.py" in text
        assert "https://github.com/sloogy/FPM/releases" in text
    smoke = read("tools/gui_smoke_test.py")
    assert "QT_QPA_PLATFORM" in smoke
    assert "MainWindow" in smoke
    assert "range(14)" in smoke
