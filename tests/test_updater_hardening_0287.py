from __future__ import annotations

import stat
import zipfile

import pytest

from updater import common


def test_manifest_asset_selection_and_semver(monkeypatch):
    manifest = common.parse_manifest(
        {
            "version": "0.2.88",
            "release_tag": "v0.2.88",
            "channel": "stable",
            "assets": {
                "windows_installer": {
                    "url": "https://example.invalid/setup.exe",
                    "sha256": "a" * 64,
                    "type": "installer",
                },
                "windows": {
                    "url": "https://example.invalid/portable.zip",
                    "sha256": "b" * 64,
                    "type": "portable-zip",
                },
            },
        }
    )
    assert manifest.assets["windows_installer"].asset_type == "installer"
    monkeypatch.setattr(common, "read_install_type", lambda: "windows_installer")
    assert common.preferred_asset_keys("windows")[:2] == ["windows_installer", "windows"]
    assert common.is_newer("0.2.88", "0.2.86") is True
    assert common.is_newer("0.2.86", "0.2.88") is False
    assert common.is_newer("not-a-version", "0.2.88") is False


def test_safe_extract_zip_extracts_regular_files(tmp_path):
    archive_path = tmp_path / "safe.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("FountainPenManager/readme.txt", "ok")

    destination = tmp_path / "staging"
    common.safe_extract_zip(archive_path, destination)
    assert (destination / "FountainPenManager" / "readme.txt").read_text() == "ok"


@pytest.mark.parametrize("unsafe_name", ["../escape.txt", "/absolute.txt", "C:/escape.txt", "folder/../../escape.txt"])
def test_safe_extract_zip_rejects_unsafe_paths(tmp_path, unsafe_name):
    archive_path = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(unsafe_name, "blocked")

    destination = tmp_path / "staging"
    with pytest.raises(ValueError, match="Unsicherer Pfad"):
        common.safe_extract_zip(archive_path, destination)
    assert not (tmp_path / "escape.txt").exists()


def test_safe_extract_zip_rejects_symlink_entries(tmp_path):
    archive_path = tmp_path / "symlink.zip"
    info = zipfile.ZipInfo("link")
    info.create_system = 3
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(info, "../outside")

    with pytest.raises(ValueError, match="Unsicherer Pfad"):
        common.safe_extract_zip(archive_path, tmp_path / "staging")
