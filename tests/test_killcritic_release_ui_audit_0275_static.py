"""v0.2.89: KILLCRITIC release/UI audit hardening guards."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_readme_referenced_markdown_files_exist():
    import re
    readme = read("README.md")
    refs = re.findall(r"`([^`]+\.md)`", readme)
    missing = [ref for ref in refs if not (ROOT / ref).exists()]
    assert not missing, missing


def test_event_bus_has_headless_fallback_for_logic_imports():
    src = read("logic/event_bus.py")
    assert "except ModuleNotFoundError" in src
    assert "class _SignalDescriptor" in src
    assert "class _BoundSignal" in src


def test_release_version_0275_is_consistent_in_primary_files():
    assert 'APP_VERSION = "0.2.89"' in read("app_info.py")
    assert "FountainPen Manager Version 0.2.89" in read("VERSION_INFO.txt")
    assert "# FountainPen Manager v0.2.89" in read("README.md")
    assert '"version": "0.2.89"' in read("version.json")
    assert "v0.2.89" in read("latest.json.template")
    assert "v0.2.89" in read("docs/latest.json.template")


def test_no_owner_placeholder_in_release_files():
    for rel in [
        "README.md", "latest.json.template", "docs/latest.json.template",
        "installer/FountainPenManager_Setup.iss", "updater/common.py",
        "updater/github_manifest.py", "ui/update_dialog.py",
    ]:
        text = read(rel)
        assert "OWNER/FountainPenManager" not in text
        assert "github.com/sloogy/FPM" in text
