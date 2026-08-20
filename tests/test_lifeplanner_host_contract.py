import json
from pathlib import Path

from database.db import _data_dir
from logic.budget_export_service import default_bridge_dir

ROOT = Path(__file__).resolve().parents[1]


def test_manifest_and_host_paths(monkeypatch, tmp_path):
    manifest = json.loads((ROOT / "module.json").read_text(encoding="utf-8"))
    assert manifest["schema"] == "lifeplanner.module.v1"
    assert manifest["id"] == "fpm"
    monkeypatch.setenv("FPM_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LIFEPLANNER_BRIDGE_DIR", str(tmp_path / "bridge"))
    assert _data_dir() == tmp_path / "data"
    assert default_bridge_dir() == (tmp_path / "bridge").resolve()
