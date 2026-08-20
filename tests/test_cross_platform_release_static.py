"""Static regression checks for the Windows and Linux release pipeline."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_release_workflow_builds_windows_and_linux():
    workflow = read(".github/workflows/windows-release.yml")
    assert "Cross-platform gated release" in workflow
    assert "windows-latest" in workflow
    assert "ubuntu-latest" in workflow
    assert "FountainPenManager-windows" in workflow
    assert "FountainPenManager-linux" in workflow
    assert "python -m PyInstaller FPM.spec --noconfirm --clean" in workflow
    assert "gh release create" in workflow
    assert "softprops/action-gh-release" not in workflow


def test_release_workflow_keeps_installer_separate():
    workflow = read(".github/workflows/windows-release.yml")
    assert "FountainPenManager-installer" in workflow
    assert "installer\\FountainPenManager_Setup.iss" in workflow
    assert "needs:" in workflow
    assert "Publish tagged prerelease or verified signed release" in workflow


def test_release_asset_builder_supports_both_platforms():
    source = read("tools/build_release_assets.py")
    for value in (
        "portable-windows.zip",
        "portable-linux.zip",
        "start-windows.cmd",
        "start-linux.sh",
        '"windows"',
        '"linux"',
        "windows_installer",
        "SHA256SUMS.txt",
        "latest.json",
    ):
        assert value in source


def test_updater_supports_linux_manifest_asset():
    source = read("updater/common.py")
    assert 'return "linux"' in source
    assert 'keys.extend(["linux", "portable_zip"])' in source
    assert (
        'return "FountainPenManager.exe" if is_windows() '
        'else "FountainPenManager"'
    ) in source


def test_pyinstaller_spec_is_cross_platform():
    spec = read("FPM.spec")
    assert "import sys" in spec
    assert 'sys.platform.startswith("win")' in spec
    assert 'name="FountainPenManager"' in spec
    assert "console=False" in spec
    assert "upx=False" in spec


def test_linux_release_doc_is_consolidated_and_multilingual():
    path = ROOT / "docs" / "LINUX_RELEASE.md"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    for heading in ("## Deutsch", "## English", "## Français"):
        assert heading in text
    assert "start-linux.sh" in text
    assert "FPM_DATA_DIR" in text
    assert "_internal/" in text


def test_release_workflow_has_no_unlocked_or_cross_shell_fallback():
    workflow = read(".github/workflows/windows-release.yml")
    assert "Test-Path constraints.lock" not in workflow
    assert "pip install -r requirements.txt" not in workflow
    assert "--require-hashes --only-binary=:all:" in workflow
    assert "constraints-windows.lock" in workflow
    assert "constraints-linux.lock" in workflow
    assert "name_audit.py" in workflow and "bandit" in workflow


def test_tagged_release_requires_verified_authenticode():
    workflow = read(".github/workflows/windows-release.yml")
    assert "WINDOWS_SIGNING_CERT_BASE64" in workflow
    assert "signtool" in workflow.lower()
    assert "verify /pa /all /v" in workflow
    assert "needs: [build, installer]" in workflow
