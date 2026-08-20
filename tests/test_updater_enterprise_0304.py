"""Enterprise control-flow tests for the release updater (v0.3.04).

All network, process and filesystem boundaries are isolated.  The goal is to
exercise the fail-closed branches that matter for a shipped updater rather than
merely importing the modules.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from updater import apply_update, check_update, startup_check
from updater.common import AssetInfo, Manifest


def manifest(*, version="9.9.9", assets=None) -> Manifest:
    return Manifest(
        version=version,
        release_tag=f"v{version}",
        channel="stable",
        assets=assets or {
            "linux": AssetInfo("https://example.invalid/fpm.zip", "abc", "portable-zip")
        },
    )


def patch_check_base(monkeypatch, tmp_path, *, m=None):
    out = []
    monkeypatch.setattr(check_update, "enable_utf8_console", lambda: None)
    monkeypatch.setattr(check_update, "read_current_version", lambda: "1.0.0")
    monkeypatch.setattr(check_update, "fetch_manifest", lambda *_: m or manifest())
    monkeypatch.setattr(check_update, "detect_platform_key", lambda: "linux")
    monkeypatch.setattr(check_update, "preferred_asset_keys", lambda _: ["linux"])
    monkeypatch.setattr(check_update, "cache_zip_path", lambda v: tmp_path / "cache" / f"{v}.zip")
    monkeypatch.setattr(check_update, "staging_dir_for", lambda v: tmp_path / "staging" / v)
    monkeypatch.setattr(check_update, "write_check_result", lambda value: out.append(value))
    monkeypatch.setattr(check_update, "prune_other_staging", lambda *a: None)
    monkeypatch.setattr(check_update, "write_staged_marker", lambda *a: tmp_path / "marker")
    return out


def fake_download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(b"payload")


def test_check_manifest_failure(monkeypatch, tmp_path):
    out = patch_check_base(monkeypatch, tmp_path)
    monkeypatch.setattr(check_update, "fetch_manifest", lambda *_: (_ for _ in ()).throw(OSError("offline")))
    assert check_update.main() == 2
    assert out[-1]["available"] is False and "offline" in out[-1]["error"]


def test_check_missing_asset_and_no_update(monkeypatch, tmp_path):
    out = patch_check_base(monkeypatch, tmp_path, m=manifest(assets={"windows": AssetInfo("u", "h")}))
    assert check_update.main() == 3
    assert "Kein Asset" in out[-1]["error"]

    out = patch_check_base(monkeypatch, tmp_path, m=manifest(version="1.0.0"))
    monkeypatch.setattr(check_update, "is_newer", lambda *_: False)
    assert check_update.main() == 0
    assert out[-1]["available"] is False


def test_check_download_hash_and_missing_hash_fail_closed(monkeypatch, tmp_path):
    out = patch_check_base(monkeypatch, tmp_path)
    monkeypatch.setattr(check_update, "is_newer", lambda *_: True)
    monkeypatch.setattr(check_update, "download_file", lambda *_: (_ for _ in ()).throw(OSError("denied")))
    assert check_update.main() == 4
    assert "Download fehlgeschlagen" in out[-1]["error"]

    out = patch_check_base(monkeypatch, tmp_path)
    monkeypatch.setattr(check_update, "is_newer", lambda *_: True)
    monkeypatch.setattr(check_update, "download_file", fake_download)
    monkeypatch.setattr(check_update, "sha256_file", lambda *_: "wrong")
    assert check_update.main() == 5
    assert out[-1]["error"] == "SHA256 stimmt nicht"

    empty_hash = manifest(assets={"linux": AssetInfo("https://example.invalid/fpm.zip", "", "portable-zip")})
    out = patch_check_base(monkeypatch, tmp_path, m=empty_hash)
    monkeypatch.setattr(check_update, "is_newer", lambda *_: True)
    monkeypatch.setattr(check_update, "download_file", fake_download)
    assert check_update.main() == 5
    assert "Kein SHA256" in out[-1]["error"]


def test_check_zip_success_and_existing_staging(monkeypatch, tmp_path):
    digest = hashlib.sha256(b"payload").hexdigest()
    m = manifest(assets={"linux": AssetInfo("https://example.invalid/fpm.zip", digest, "portable-zip")})
    out = patch_check_base(monkeypatch, tmp_path, m=m)
    monkeypatch.setattr(check_update, "is_newer", lambda *_: True)
    monkeypatch.setattr(check_update, "download_file", fake_download)
    monkeypatch.setattr(check_update, "safe_extract_zip", lambda z, d: (d.mkdir(parents=True, exist_ok=True), (d / "main.py").write_text("x")))
    assert check_update.main() == 0
    assert out[-1]["staged"] is True

    # A second run must accept already-populated staging without extracting.
    out = patch_check_base(monkeypatch, tmp_path, m=m)
    monkeypatch.setattr(check_update, "is_newer", lambda *_: True)
    monkeypatch.setattr(check_update, "download_file", fake_download)
    monkeypatch.setattr(check_update, "safe_extract_zip", lambda *_: pytest.fail("must not extract twice"))
    assert check_update.main() == 0


def test_check_empty_zip_installer_and_raw_binary(monkeypatch, tmp_path):
    digest = hashlib.sha256(b"payload").hexdigest()
    m = manifest(assets={"linux": AssetInfo("https://example.invalid/fpm.zip", digest, "portable-zip")})
    out = patch_check_base(monkeypatch, tmp_path, m=m)
    monkeypatch.setattr(check_update, "is_newer", lambda *_: True)
    monkeypatch.setattr(check_update, "download_file", fake_download)
    monkeypatch.setattr(check_update, "safe_extract_zip", lambda z, d: d.mkdir(parents=True, exist_ok=True))
    assert check_update.main() == 6
    assert out[-1]["error"] == "Staging leer"

    installer = manifest(assets={"linux": AssetInfo("https://example.invalid/setup.bin", digest, "installer")})
    out = patch_check_base(monkeypatch, tmp_path / "installer", m=installer)
    monkeypatch.setattr(check_update, "is_newer", lambda *_: True)
    monkeypatch.setattr(check_update, "download_file", fake_download)
    assert check_update.main() == 0
    assert next((tmp_path / "installer" / "staging" / "9.9.9").glob("*.exe")).is_file()

    raw = manifest(assets={"linux": AssetInfo("https://example.invalid/fpm.bin", digest, "binary")})
    out = patch_check_base(monkeypatch, tmp_path / "raw", m=raw)
    monkeypatch.setattr(check_update, "is_newer", lambda *_: True)
    monkeypatch.setattr(check_update, "download_file", fake_download)
    monkeypatch.setattr(check_update, "update_target_exe_filename", lambda: "FountainPenManager")
    assert check_update.main() == 0
    assert (tmp_path / "raw" / "staging" / "9.9.9" / "FountainPenManager").is_file()


def test_check_staging_exception(monkeypatch, tmp_path):
    digest = hashlib.sha256(b"payload").hexdigest()
    m = manifest(assets={"linux": AssetInfo("https://example.invalid/fpm.zip", digest, "portable-zip")})
    out = patch_check_base(monkeypatch, tmp_path, m=m)
    monkeypatch.setattr(check_update, "is_newer", lambda *_: True)
    monkeypatch.setattr(check_update, "download_file", fake_download)
    monkeypatch.setattr(check_update, "safe_extract_zip", lambda *_: (_ for _ in ()).throw(OSError("bad zip")))
    assert check_update.main() == 6
    assert "Staging fehlgeschlagen" in out[-1]["error"]


def patch_startup(monkeypatch, *, m=None):
    out = []
    monkeypatch.setattr(startup_check, "enable_utf8_console", lambda: None)
    monkeypatch.setattr(startup_check, "read_current_version", lambda: "1.0.0")
    monkeypatch.setattr(startup_check, "clear_startup_check_result", lambda: None)
    monkeypatch.setattr(startup_check, "fetch_manifest", lambda *_args, **_kw: m or manifest())
    monkeypatch.setattr(startup_check, "detect_platform_key", lambda: "linux")
    monkeypatch.setattr(startup_check, "preferred_asset_keys", lambda _: ["linux"])
    monkeypatch.setattr(startup_check, "write_startup_check_result", lambda value: out.append(value))
    return out


def test_startup_check_all_control_paths(monkeypatch):
    out = patch_startup(monkeypatch)
    monkeypatch.setattr(startup_check, "fetch_manifest", lambda *_a, **_k: (_ for _ in ()).throw(OSError("offline")))
    assert startup_check.main() == 2
    assert out[-1]["downloaded"] is False

    out = patch_startup(monkeypatch, m=manifest(assets={"windows": AssetInfo("u", "h")}))
    assert startup_check.main() == 3
    assert "Kein Asset" in out[-1]["error"]

    out = patch_startup(monkeypatch)
    monkeypatch.setattr(startup_check, "is_newer", lambda *_: True)
    assert startup_check.main() == 0 and out[-1]["available"] is True

    out = patch_startup(monkeypatch)
    monkeypatch.setattr(startup_check, "is_newer", lambda *_: False)
    assert startup_check.main() == 0 and out[-1]["available"] is False


def patch_apply_base(monkeypatch, tmp_path):
    app = tmp_path / "app"
    updates = tmp_path / "updates"
    app.mkdir(parents=True, exist_ok=True)
    for name in ("cache", "staging", "backup"):
        (updates / name).mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(apply_update, "enable_utf8_console", lambda: None)
    monkeypatch.setattr(apply_update, "app_dir", lambda: app)
    monkeypatch.setattr(apply_update, "updates_dir", lambda: updates)
    monkeypatch.setattr(apply_update, "staging_dir_for", lambda v: updates / "staging" / v)
    monkeypatch.setattr(apply_update, "backup_current_zip", lambda *a, **k: updates / "backup" / "rollback.zip")
    monkeypatch.setattr(apply_update, "_restart_after_update", lambda *_: None)
    return app, updates


def test_apply_version_selection_and_helpers(monkeypatch, tmp_path):
    app, updates = patch_apply_base(monkeypatch, tmp_path)
    for v in ("1.2.3", "2.0.0"):
        d = updates / "staging" / v
        d.mkdir(parents=True)
        (d / "x").write_text("x")
    monkeypatch.setattr(apply_update, "read_check_result", lambda: {"staged_version": "1.2.3"})
    assert apply_update.target_staged_version() == "1.2.3"
    monkeypatch.setattr(apply_update, "read_check_result", lambda: {"staged_version": "missing"})
    assert apply_update.target_staged_version() == "2.0.0"

    src = tmp_path / "src"
    src.mkdir()
    (src / "FountainPenManager").write_text("new")
    monkeypatch.setattr(apply_update, "update_target_exe_filename", lambda: "FountainPenManager")
    monkeypatch.setattr(apply_update, "current_exe_filename", lambda: "old")
    monkeypatch.setattr(apply_update, "stable_exe_filename", lambda: "FountainPenManager")
    assert apply_update._staged_target_binary(src).name == "FountainPenManager"
    assert apply_update._launch_exe_filename(src) == "FountainPenManager"

    target = app / "FountainPenManager"
    target.write_text("old")
    apply_update._replace_binary_inplace(src / "FountainPenManager", target)
    assert target.read_text() == "new"
    assert not target.with_name(target.name + ".new").exists()


def test_apply_batch_builders_and_restart(monkeypatch, tmp_path):
    batch = apply_update._build_windows_helper_batch(
        tmp_path / "src", tmp_path / "dst", "old.exe", "new.exe", tmp_path / "log.txt"
    )
    assert "robocopy" in batch and "old.exe" in batch and "new.exe" in batch
    installer = apply_update._build_windows_installer_helper_batch(
        setup=tmp_path / "setup.exe", app_root=tmp_path / "app", data_dir=tmp_path / "data",
        wait_exe="FountainPenManager.exe", log_path=tmp_path / "log.txt",
    )
    assert "/UPDATE_MODE=1" in installer and "setup.exe" in installer

    monkeypatch.delenv("FPM_UPDATER_NO_RESTART", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(apply_update.sys, "frozen", False, raising=False)
    calls = []
    monkeypatch.setattr(apply_update.subprocess, "Popen", lambda *a, **k: calls.append((a, k)))
    monkeypatch.setattr(apply_update, "app_dir", lambda: tmp_path)
    apply_update._restart_after_update(tmp_path)
    assert calls


def test_apply_installer_and_windows_helpers(monkeypatch, tmp_path):
    app, updates = patch_apply_base(monkeypatch, tmp_path)
    src = tmp_path / "installer"
    src.mkdir()
    (src / "FountainPenManager_Setup.exe").write_bytes(b"exe")
    monkeypatch.setattr(apply_update, "is_windows", lambda: False)
    assert apply_update._apply_via_windows_installer(src, {}) == 10
    monkeypatch.setattr(apply_update, "is_windows", lambda: True)
    empty = tmp_path / "empty"; empty.mkdir()
    assert apply_update._apply_via_windows_installer(empty, {}) == 11

    monkeypatch.setattr(apply_update, "_read_installation_marker", lambda: {"data_directory": str(tmp_path / "data")})
    monkeypatch.setattr(apply_update, "current_exe_filename", lambda: "FountainPenManager.exe")
    calls = []
    monkeypatch.setattr(apply_update.subprocess, "Popen", lambda *a, **k: calls.append((a, k)))
    assert apply_update._apply_via_windows_installer(src, {}) == 0
    assert (updates / "apply_installer_update.bat").is_file() and calls

    monkeypatch.setattr(apply_update.subprocess, "Popen", lambda *a, **k: (_ for _ in ()).throw(OSError("blocked")))
    assert apply_update._apply_via_windows_installer(src, {}) == 12

    portable = tmp_path / "portable"; portable.mkdir()
    (portable / "FountainPenManager.exe").write_bytes(b"exe")
    monkeypatch.setattr(apply_update, "_launch_exe_filename", lambda *_: "FountainPenManager.exe")
    monkeypatch.setattr(apply_update.subprocess, "Popen", lambda *a, **k: None)
    assert apply_update._apply_via_windows_helper(portable) == 0
    assert (updates / "apply_update.bat").is_file()
    monkeypatch.setattr(apply_update.subprocess, "Popen", lambda *a, **k: (_ for _ in ()).throw(OSError("blocked")))
    assert apply_update._apply_via_windows_helper(portable) == 7


def test_apply_main_dispatch_and_linux_paths(monkeypatch, tmp_path):
    app, updates = patch_apply_base(monkeypatch, tmp_path)
    monkeypatch.setattr(apply_update, "target_staged_version", lambda: None)
    assert apply_update.main() == 2

    monkeypatch.setattr(apply_update, "target_staged_version", lambda: "1.2.3")
    assert apply_update.main() == 3

    staging = updates / "staging" / "1.2.3"
    staging.mkdir(parents=True)
    (staging / "new.txt").write_text("new")
    monkeypatch.setattr(apply_update, "find_staged_root", lambda p: p)
    monkeypatch.setattr(apply_update, "read_marker", lambda p: {"asset_type": "installer"})
    monkeypatch.setattr(apply_update, "_apply_via_windows_installer", lambda *_: 17)
    assert apply_update.main() == 17

    monkeypatch.setattr(apply_update, "read_marker", lambda p: {})
    monkeypatch.setattr(apply_update, "is_windows", lambda: True)
    monkeypatch.setattr(apply_update, "_apply_via_windows_helper", lambda *_: 18)
    assert apply_update.main() == 18

    monkeypatch.setattr(apply_update, "is_windows", lambda: False)
    binary = staging / "FountainPenManager"
    binary.write_text("binary")
    monkeypatch.setattr(apply_update, "_staged_target_binary", lambda *_: binary)
    monkeypatch.setattr(apply_update, "update_target_exe_filename", lambda: "FountainPenManager")
    assert apply_update.main() == 0
    assert (app / "FountainPenManager").read_text() == "binary"

    monkeypatch.setattr(apply_update, "_replace_binary_inplace", lambda *_: (_ for _ in ()).throw(OSError("locked")))
    assert apply_update.main() == 8

    monkeypatch.setattr(apply_update, "_staged_target_binary", lambda *_: None)
    monkeypatch.setattr(apply_update, "remove_paths", lambda *_a, **_k: None)
    monkeypatch.setattr(apply_update, "copy_new", lambda *_a, **_k: None)
    assert apply_update.main() == 0
    monkeypatch.setattr(apply_update, "copy_new", lambda *_a, **_k: (_ for _ in ()).throw(OSError("copy")))
    assert apply_update.main() == 9
