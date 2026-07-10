"""Static checks for Windows portable/installer release packaging."""
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
    for lang in ("de.json", "en.json", "fr.json"):
        assert lang in spec
    assert "sqlalchemy.dialects.sqlite" in spec


def test_inno_setup_script_is_release_ready():
    iss = read("installer/FountainPenManager_Setup.iss")
    assert '#define MyAppVersion "0.2.90"' in iss
    assert "FountainPenManager.exe" in iss
    assert "OutputBaseFilename=FountainPenManager_Setup_{#MyAppVersion}" in iss
    assert "WizardStyle=modern" in iss
    assert "recursesubdirs" in iss
    assert "German.isl" in iss
    assert "French.isl" in iss
    assert "Default.isl" in iss


def test_build_script_creates_budgettool_style_assets():
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


def test_windows_github_workflow_builds_on_windows_runner():
    workflow = read(".github/workflows/windows-release.yml")
    assert "windows-latest" in workflow
    assert "python-version: '3.12'" in workflow
    assert "requirements-build.txt" in workflow
    assert "innosetup" in workflow.lower()
    assert "tools/build_windows.py --clean" in workflow
    assert "softprops/action-gh-release" in workflow


def test_multilingual_windows_release_docs_exist():
    for rel in (
        "docs/WINDOWS_RELEASE_DE.md",
        "docs/WINDOWS_RELEASE_EN.md",
        "docs/WINDOWS_RELEASE_FR.md",
    ):
        path = ROOT / rel
        assert path.exists(), rel
        assert "FPM_DATA_DIR" in path.read_text(encoding="utf-8")
