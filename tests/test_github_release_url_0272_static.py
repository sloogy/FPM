"""v0.2.78 GitHub release URL finalization checks."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASES = "https://github.com/sloogy/FPM/releases"
MANIFEST = f"{RELEASES}/latest/download/latest.json"


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_updater_uses_real_release_manifest_url():
    assert f'DEFAULT_MANIFEST_URL = "{MANIFEST}"' in read("updater/common.py")
    assert f'DEFAULT_MANIFEST_URL = "{MANIFEST}"' in read("updater/github_manifest.py")


def test_update_dialog_and_installer_use_real_releases_url():
    assert f'GITHUB_RELEASES_URL = "{RELEASES}"' in read("ui/update_dialog.py")
    assert f'#define MyAppURL "{RELEASES}"' in read("installer/FountainPenManager_Setup.iss")


def test_latest_templates_and_build_tools_use_real_repo():
    for rel in (
        "latest.json.template",
        "docs/latest.json.template",
        "tools/sync_version.py",
        "tools/build_windows.py",
        "updater/generate_manifest.py",
    ):
        text = read(rel)
        assert "https://github.com/sloogy/FPM/releases" in text
        assert "OWNER/FountainPenManager" not in text
        assert "github.com/OWNER" not in text


def test_release_package_has_no_active_owner_placeholder():
    active_paths = [
        "updater/common.py",
        "updater/github_manifest.py",
        "ui/update_dialog.py",
        "tools/build_windows.py",
        "tools/sync_version.py",
        "installer/FountainPenManager_Setup.iss",
        "latest.json.template",
        "docs/latest.json.template",
        "README.md",
    ]
    for rel in active_paths:
        text = read(rel)
        assert "OWNER/FountainPenManager" not in text
        assert "github.com/OWNER" not in text
