from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_windows_path_guard_is_wired_into_ci():
    assert (ROOT / "tools/check_windows_paths.py").is_file()
    for rel in (".github/workflows/release-check.yml", ".github/workflows/windows-release.yml"):
        assert "python tools/check_windows_paths.py" in (ROOT / rel).read_text(encoding="utf-8")


def test_release_docs_are_consolidated():
    assert (ROOT / "CHANGELOG.md").is_file()
    assert (ROOT / "RELEASE_REPORT.md").is_file()
    assert (ROOT / "docs/history").is_dir()
    assert (ROOT / "docs/BENUTZERHANDBUCH_DE.md").is_file()
    assert (ROOT / "docs/LINUX_RELEASE.md").is_file()
