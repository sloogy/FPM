"""Guards for the deterministic 1000-loop release audit."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_killcritic_defaults_to_real_1000_loops_and_is_configurable():
    source = (ROOT / "tools" / "killcritic_1000_loop_audit.py").read_text(
        encoding="utf-8"
    )
    assert 'os.environ.get("FPM_KILLCRITIC_LOOPS", "1000")' in source
    assert source.count("@lru_cache(maxsize=None)") >= 3
    assert "loops = 20" not in source
    assert "loops < 1 or loops > 10000" in source


def test_release_workflow_executes_killcritic_on_both_matrix_platforms():
    workflow = (ROOT / ".github" / "workflows" / "windows-release.yml").read_text(
        encoding="utf-8"
    )
    assert "python tools/killcritic_1000_loop_audit.py" in workflow
    assert "windows-latest" in workflow
    assert "ubuntu-latest" in workflow
