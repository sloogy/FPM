"""Static checks for Windows/Linux portable and installer packaging."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_portable_data_dir_override_exists_without_breaking_default():
    src = read("database/db.py")
    assert "FPM_DATA_DIR" in src
    assert "Path.home() / \".fpm_data\"" in src
    assert "d.mkdir(parents=True, exist_ok=True)" in src


def test_pyinstaller_spec_collects_required_runtime_data():
    spec = read("FPM.spec")
    assert "FountainPenManager" in spec
    assert "console=False" in spec
    assert "assets" in spec and "fountainpen.ico" in spec
    assert 'sys.platform.startswith("win")' in spec
    for lang in ("de.json", "en.json", "fr.json"):
        assert lang in spec
    assert "sqlalchemy.dialects.sqlite" in spec


def test_inno_setup_script_is_release_ready_and_version_synced():
    from app_info import APP_VERSION

    iss = read("installer/FountainPenManager_Setup.iss")
    assert f'#define MyAppVersion "{APP_VERSION}"' in iss
    assert "FountainPenManager.exe" in iss
    assert "OutputBaseFilename=FountainPenManager_Setup_{#MyAppVersion}" in iss
    assert 'Source: "dist\\FountainPenManager\\*"' in iss
    assert "WizardStyle=modern" in iss
    assert "recursesubdirs" in iss
    assert "German.isl" in iss
    assert "French.isl" in iss
    assert "Default.isl" in iss


def test_local_windows_build_script_still_creates_supported_assets():
    src = read("tools/build_windows.py")
    expected_names = [
        "portable-windows.zip",
        "FountainPenManager_Setup_",
        "latest.json",
        "SHA256SUMS.txt",
        "windows_installer",
        "portable-zip",
    ]
    for needle in expected_names:
        assert needle in src
    assert "start-windows.cmd" in src
    assert "FPM_DATA_DIR=%DIR%data" in src
    assert "PyInstaller" in src
    assert "ISCC" in src


def test_release_workflow_builds_both_platforms_and_installer():
    workflow = read(".github/workflows/windows-release.yml")
    assert "windows-latest" in workflow
    assert "ubuntu-latest" in workflow
    assert "ubuntu-latest" in workflow
    assert "python-version: '3.12'" in workflow
    assert "constraints-windows.lock" in workflow
    assert "constraints-linux.lock" in workflow
    assert "--require-hashes" in workflow
    assert "innosetup" in workflow.lower()
    assert "python -m PyInstaller FPM.spec --noconfirm --clean" in workflow
    assert "tools/build_release_assets.py" in workflow
    assert "gh release create" in workflow
    assert "softprops/action-gh-release" not in workflow


def test_multilingual_windows_release_docs_exist():
    for rel in (
        "docs/WINDOWS_RELEASE_DE.md",
        "docs/WINDOWS_RELEASE_EN.md",
        "docs/WINDOWS_RELEASE_FR.md",
    ):
        path = ROOT / rel
        assert path.exists(), rel
        assert "FPM_DATA_DIR" in path.read_text(encoding="utf-8")
