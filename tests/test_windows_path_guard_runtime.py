"""Runtime tests for the Windows path guard source-tree fallback."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load_module():
    path = ROOT / "tools" / "check_windows_paths.py"
    spec = importlib.util.spec_from_file_location("check_windows_paths", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_source_fallback_prunes_generated_directories(tmp_path):
    module = load_module()
    fake_root = tmp_path / "project"
    tools = fake_root / "tools"
    tools.mkdir(parents=True)
    fake_script = tools / "check_windows_paths.py"
    fake_script.write_text("# guard", encoding="utf-8")
    (fake_root / "good.txt").write_text("ok", encoding="utf-8")
    (fake_root / "dist" / "nested").mkdir(parents=True)
    (fake_root / "dist" / "nested" / "ignored.txt").write_text("x", encoding="utf-8")

    with patch.object(module, "__file__", str(fake_script)), patch.object(
        module.subprocess, "check_output", side_effect=module.subprocess.CalledProcessError(1, "git")
    ):
        paths = module.tracked_paths()

    assert "good.txt" in paths
    assert not any(path.startswith("dist/") for path in paths)


def test_path_problem_detection_covers_windows_hazards():
    module = load_module()
    assert module.problems("bad ")
    assert module.problems("NUL.txt")
    assert module.problems("bad?.txt")
    assert not module.problems("docs/valid-name.md")
