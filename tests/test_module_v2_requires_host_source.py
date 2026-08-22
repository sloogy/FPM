import json
import stat
from pathlib import Path

from app_info import APP_VERSION
from tools.build_lifeplanner_module import build_unsigned_release_module

ROOT = Path(__file__).resolve().parents[1]


def test_module_v2_paket_nimmt_requires_host_aus_manifest(tmp_path):
    manifest = json.loads((ROOT / "module.json").read_text(encoding="utf-8"))
    runtime = tmp_path / "FountainPenManager"
    (runtime / "_internal").mkdir(parents=True)
    binary = runtime / "FountainPenManager"
    binary.write_bytes(b"runtime")
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    (runtime / "_internal" / "runtime.bin").write_bytes(b"dependency")

    target = build_unsigned_release_module(
        runtime_dir=runtime,
        runtime_name="FountainPenManager",
        platform="linux-x86_64",
        release_tag=f"v{APP_VERSION}",
        output=tmp_path / "fpm.lpmodule",
        requires_host=">=0.5.0",
    )

    import zipfile

    with zipfile.ZipFile(target) as archive:
        component = json.loads(archive.read("component.json"))
    assert component["requires_host"] == manifest["requires_host"]
