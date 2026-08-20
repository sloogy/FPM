"""Runtime regression test for combined Windows/Linux release assets."""

from __future__ import annotations

import hashlib
import json
import stat
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_combined_asset_builder_creates_verified_cross_platform_release(tmp_path):
    windows = tmp_path / "windows"
    linux = tmp_path / "linux"
    installer = tmp_path / "installer"
    out = tmp_path / "out"

    for bundle in (windows, linux):
        (bundle / "_internal").mkdir(parents=True)

    (windows / "FountainPenManager.exe").write_bytes(b"windows")
    (windows / "_internal" / "runtime.dll").write_bytes(b"dll")

    linux_binary = linux / "FountainPenManager"
    linux_binary.write_bytes(b"#!/bin/sh\nexit 0\n")
    linux_binary.chmod(linux_binary.stat().st_mode | stat.S_IXUSR)
    (linux / "_internal" / "runtime.so").write_bytes(b"so")

    installer.mkdir()
    (installer / "FountainPenManager_Setup.exe").write_bytes(b"installer")

    module_windows = tmp_path / "fpm_1.0.3_Windows_x86_64.lpmodule"
    module_linux = tmp_path / "fpm_1.0.3_Linux_x86_64.lpmodule"
    for module in (module_windows, module_linux):
        with zipfile.ZipFile(module, "w") as archive:
            archive.writestr("component.json", b"{}")
            archive.writestr("payload/module.json", b"{}")

    subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "build_release_assets.py"),
            "--version",
            "1.0.3",
            "--release-tag",
            "v1.0.3",
            "--base-url",
            "https://example.invalid/v1.0.3",
            "--windows-build-dir",
            str(windows),
            "--linux-build-dir",
            str(linux),
            "--installer-dir",
            str(installer),
            "--module-windows",
            str(module_windows),
            "--module-linux",
            str(module_linux),
            "--out-dir",
            str(out),
        ],
        check=True,
    )

    expected = {
        "FountainPenManager-v1.0.3-portable-windows.zip",
        "FountainPenManager-v1.0.3-portable-linux.zip",
        "FountainPenManager_Setup_1.0.3.exe",
        "FountainPenManager_Setup_1.0.3.zip",
        "fpm_1.0.3_Windows_x86_64.lpmodule",
        "fpm_1.0.3_Linux_x86_64.lpmodule",
        "latest.json",
        "UNSIGNED_RELEASE.txt",
        "SHA256SUMS.txt",
    }
    assert expected <= {path.name for path in out.iterdir() if path.is_file()}

    manifest = json.loads((out / "latest.json").read_text(encoding="utf-8"))
    assert manifest["version"] == "1.0.3"
    assert manifest["release_tag"] == "v1.0.3"
    assert manifest["signature_policy"] == "allow-unsigned"

    for key in (
        "windows",
        "linux",
        "windows_installer",
        "windows_installer_zip",
        "lifeplanner_windows",
        "lifeplanner_linux",
    ):
        info = manifest["assets"][key]
        asset_path = out / info["url"].rsplit("/", 1)[-1]
        assert asset_path.is_file()
        assert hashlib.sha256(asset_path.read_bytes()).hexdigest() == info["sha256"]

    with zipfile.ZipFile(out / "FountainPenManager-v1.0.3-portable-linux.zip") as archive:
        names = set(archive.namelist())
        assert {"FountainPenManager", "start-linux.sh", "data/.keep"} <= names
        for name in ("FountainPenManager", "start-linux.sh"):
            mode = archive.getinfo(name).external_attr >> 16
            assert mode & stat.S_IXUSR

    with zipfile.ZipFile(out / "FountainPenManager-v1.0.3-portable-windows.zip") as archive:
        names = set(archive.namelist())
        assert {"FountainPenManager.exe", "start-windows.cmd", "data/.keep"} <= names

    with zipfile.ZipFile(out / "FountainPenManager_Setup_1.0.3.zip") as archive:
        notice = archive.read("WINDOWS_DOWNLOAD_HINWEIS.txt").decode("utf-8")
        assert "nicht digital signiert" in notice

    warning = (out / "UNSIGNED_RELEASE.txt").read_text(encoding="utf-8")
    assert "UNSIGNED RELEASE" in warning
    assert "LifePlanner-/LiveManager-.lpmodule-Pakete" in warning
    for module in (module_windows.name, module_linux.name):
        with zipfile.ZipFile(out / module) as archive:
            assert "component.json.sig" not in archive.namelist()


def test_prerelease_asset_builder_creates_unsigned_rc_without_update_manifest(tmp_path):
    windows = tmp_path / "windows"
    linux = tmp_path / "linux"
    installer = tmp_path / "installer"
    out = tmp_path / "prerelease"
    for bundle in (windows, linux):
        (bundle / "_internal").mkdir(parents=True)
    (windows / "FountainPenManager.exe").write_bytes(b"windows")
    (windows / "_internal" / "runtime.dll").write_bytes(b"dll")
    linux_binary = linux / "FountainPenManager"
    linux_binary.write_bytes(b"#!/bin/sh\nexit 0\n")
    linux_binary.chmod(linux_binary.stat().st_mode | stat.S_IXUSR)
    (linux / "_internal" / "runtime.so").write_bytes(b"so")
    installer.mkdir()
    (installer / "FountainPenManager_Setup.exe").write_bytes(b"installer")
    module_windows = tmp_path / "fpm_1.0.3_Windows_x86_64.lpmodule"
    module_linux = tmp_path / "fpm_1.0.3_Linux_x86_64.lpmodule"
    for module in (module_windows, module_linux):
        with zipfile.ZipFile(module, "w") as archive:
            archive.writestr("component.json", b"{}")
            archive.writestr("payload/module.json", b"{}")

    subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "build_release_assets.py"),
            "--prerelease",
            "--version",
            "1.0.3",
            "--release-tag",
            "v1.0.3-rc.1",
            "--windows-build-dir",
            str(windows),
            "--linux-build-dir",
            str(linux),
            "--installer-dir",
            str(installer),
            "--module-windows",
            str(module_windows),
            "--module-linux",
            str(module_linux),
            "--out-dir",
            str(out),
        ],
        check=True,
    )

    expected = {
        "FountainPenManager-v1.0.3-rc.1-portable-windows.zip",
        "FountainPenManager-v1.0.3-rc.1-portable-linux.zip",
        "FountainPenManager_Setup_1.0.3-rc.1.exe",
        "FountainPenManager_Setup_1.0.3-rc.1.zip",
        "fpm_1.0.3_Windows_x86_64.lpmodule",
        "fpm_1.0.3_Linux_x86_64.lpmodule",
        "UNSIGNED_PRERELEASE.txt",
        "SHA256SUMS.txt",
    }
    assert expected == {path.name for path in out.iterdir() if path.is_file()}
    assert not (out / "latest.json").exists()
    warning = (out / "UNSIGNED_PRERELEASE.txt").read_text(encoding="utf-8")
    assert "UNSIGNED TEST BUILD" in warning
    assert "LifePlanner-/LiveManager-.lpmodule-Pakete sind ebenfalls unsigniert" in warning
    for module in (module_windows.name, module_linux.name):
        with zipfile.ZipFile(out / module) as archive:
            assert "component.json.sig" not in archive.namelist()
    with zipfile.ZipFile(out / "FountainPenManager_Setup_1.0.3-rc.1.zip") as archive:
        notice = archive.read("WINDOWS_DOWNLOAD_HINWEIS.txt").decode("utf-8")
        assert "nicht digital signiert" in notice

    for line in (out / "SHA256SUMS.txt").read_text(encoding="ascii").splitlines():
        digest, filename = line.split("  ", 1)
        assert hashlib.sha256((out / filename).read_bytes()).hexdigest() == digest
