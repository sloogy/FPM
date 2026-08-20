from pathlib import Path
import json

from app_info import APP_VERSION
from tools.build_lifeplanner_module import module_asset_name

ROOT = Path(__file__).resolve().parents[1]


def test_lifeplanner_manifest_and_integrated_release_assets_are_defined():
    manifest = json.loads((ROOT / "module.json").read_text(encoding="utf-8"))
    assert manifest["version"] == APP_VERSION
    assert manifest["windows_executable"] == "FountainPenManager/FountainPenManager.exe"
    assert manifest["linux_executable"] == "FountainPenManager/FountainPenManager"
    assert module_asset_name("fpm", APP_VERSION, "windows-x86_64").endswith("Windows_x86_64.lpmodule")
    assert module_asset_name("fpm", APP_VERSION, "linux-x86_64").endswith("Linux_x86_64.lpmodule")
    assert (ROOT / "tools" / "runtime_artifact.py").is_file()
    assert (ROOT / "tools" / "lifeplanner_host_contract.py").is_file()
    assert not (ROOT / ".github" / "workflows" / "lifeplanner-module-release.yml").exists()
