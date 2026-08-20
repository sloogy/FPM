"""Regression tests for v0.3.04 Enterprise hardening."""
from __future__ import annotations

import json
import socket
import sqlite3
import threading
import time
import urllib.error
import zipfile
from pathlib import Path

import pytest
import yaml

from database import db
from logic import log_utils, media_storage_service, network_security, pen_dimensions_service
from updater import common as updater_common


def _dns(ip: str):
    return [(socket.AF_INET6 if ":" in ip else socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 443, 0, 0) if ":" in ip else (ip, 443))]


@pytest.mark.parametrize(
    "url,ip",
    [
        ("http://127.0.0.1/internal.png", "127.0.0.1"),
        ("http://10.0.0.5/internal.png", "10.0.0.5"),
        ("http://169.254.169.254/latest/meta-data", "169.254.169.254"),
        ("http://[::1]/internal.png", "::1"),
        ("http://192.168.1.1/admin", "192.168.1.1"),
    ],
)
def test_public_url_policy_rejects_non_global_targets(monkeypatch, url, ip):
    monkeypatch.setattr(network_security.socket, "getaddrinfo", lambda *a, **k: _dns(ip))
    with pytest.raises(network_security.UnsafeRemoteUrlError):
        network_security.validate_public_http_url(url)


def test_public_url_policy_rejects_credentials_and_localhost(monkeypatch):
    with pytest.raises(network_security.UnsafeRemoteUrlError):
        network_security.validate_public_http_url("https://user:secret@example.com/x")
    with pytest.raises(network_security.UnsafeRemoteUrlError):
        network_security.validate_public_http_url("http://localhost/x")
    with pytest.raises(network_security.UnsafeRemoteUrlError):
        network_security.validate_public_http_url("file:///etc/passwd")


def test_active_image_download_blocks_ssrf_before_network(monkeypatch):
    opened = []
    monkeypatch.setattr(network_security.socket, "getaddrinfo", lambda *a, **k: _dns("127.0.0.1"))
    monkeypatch.setattr(media_storage_service._opener, "open", lambda *a, **k: opened.append(True))
    with pytest.raises(network_security.UnsafeRemoteUrlError):
        media_storage_service.download_image_bytes("http://127.0.0.1/secret.png")
    assert opened == []


def test_redirect_and_final_url_are_revalidated(monkeypatch):
    def fake_dns(host, *args, **kwargs):
        return _dns("127.0.0.1" if host == "internal.invalid" else "93.184.216.34")

    monkeypatch.setattr(network_security.socket, "getaddrinfo", fake_dns)
    handler = network_security.SafePublicRedirectHandler()
    with pytest.raises(urllib.error.HTTPError):
        handler.redirect_request(None, None, 302, "Found", {}, "http://internal.invalid/private")

    class Response:
        def geturl(self):
            return "http://internal.invalid/private"
        def close(self):
            self.closed = True
    class Opener:
        def open(self, *args, **kwargs):
            return Response()
    with pytest.raises(network_security.UnsafeRemoteUrlError):
        network_security.open_public_http_url(
            "https://example.invalid/start", timeout_s=1, opener=Opener()
        )


def test_connected_peer_blocks_dns_rebinding_to_private_ip():
    class Socket:
        def getpeername(self):
            return ("127.0.0.1", 443)

    class Raw:
        _sock = Socket()

    class Buffered:
        raw = Raw()

    class Response:
        fp = Buffered()

    with pytest.raises(network_security.UnsafeRemoteUrlError, match="Gegenstelle"):
        network_security.validate_connected_peer(Response())


def test_connected_peer_accepts_public_ip():
    class Socket:
        def getpeername(self):
            return ("93.184.216.34", 443)

    class Raw:
        _sock = Socket()

    class Buffered:
        raw = Raw()

    class Response:
        fp = Buffered()

    network_security.validate_connected_peer(Response())


def test_secondary_reference_fetch_uses_central_guard(monkeypatch):
    monkeypatch.setattr(network_security.socket, "getaddrinfo", lambda *a, **k: _dns("127.0.0.1"))
    with pytest.raises(network_security.UnsafeRemoteUrlError):
        pen_dimensions_service._fetch_url_text("http://127.0.0.1/spec")


def test_image_download_cancel_closes_response(monkeypatch):
    monkeypatch.setattr(network_security.socket, "getaddrinfo", lambda *a, **k: _dns("93.184.216.34"))

    class BlockingResponse:
        def __init__(self):
            self.closed = threading.Event()
        def geturl(self):
            return "https://example.invalid/image.png"
        def read(self, _size):
            self.closed.wait(2)
            return b""
        def close(self):
            self.closed.set()

    response = BlockingResponse()
    monkeypatch.setattr(media_storage_service._opener, "open", lambda *a, **k: response)
    op = media_storage_service.ImageDownloadOperation("https://example.invalid/image.png")
    result = {}

    def run():
        try:
            op.download()
        except Exception as exc:  # captured for assertion
            result["exc"] = exc

    thread = threading.Thread(target=run)
    thread.start()
    time.sleep(0.05)
    op.cancel()
    thread.join(2)
    assert not thread.is_alive()
    assert isinstance(result.get("exc"), media_storage_service.DownloadCancelledError)
    assert response.closed.is_set()



def test_updater_manifest_and_asset_paths_use_central_guard(monkeypatch, tmp_path):
    monkeypatch.setattr(network_security.socket, "getaddrinfo", lambda *a, **k: _dns("127.0.0.1"))
    with pytest.raises(network_security.UnsafeRemoteUrlError):
        updater_common.fetch_manifest("http://127.0.0.1/latest.json")
    with pytest.raises(network_security.UnsafeRemoteUrlError):
        updater_common.download_file("http://127.0.0.1/update.zip", tmp_path / "update.zip")


def test_updater_download_is_atomic_and_removes_partial(monkeypatch, tmp_path):
    class Response:
        def __init__(self, chunks):
            self.chunks = iter(chunks)
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self, _size):
            item = next(self.chunks, b"")
            if isinstance(item, BaseException):
                raise item
            return item

    monkeypatch.setattr(
        updater_common, "open_public_http_url",
        lambda *a, **k: Response([b"abc", b"def", b""]),
    )
    target = tmp_path / "update.zip"
    updater_common.download_file("https://example.invalid/update.zip", target)
    assert target.read_bytes() == b"abcdef"
    assert not target.with_name(target.name + ".partial").exists()

    target.write_bytes(b"known-good")
    monkeypatch.setattr(
        updater_common, "open_public_http_url",
        lambda *a, **k: Response([b"new", OSError("connection lost")]),
    )
    with pytest.raises(OSError):
        updater_common.download_file("https://example.invalid/update.zip", target)
    assert target.read_bytes() == b"known-good"
    assert not target.with_name(target.name + ".partial").exists()

def _create_db(path: Path) -> None:
    with sqlite3.connect(path) as con:
        con.execute("CREATE TABLE sample(id INTEGER PRIMARY KEY, value TEXT)")
        con.execute("INSERT INTO sample(value) VALUES ('kept')")
        con.commit()


def test_sqlite_backup_is_atomic_verified_and_restorable(tmp_path):
    source = tmp_path / "source.db"
    target = tmp_path / "backup" / "source.db"
    _create_db(source)
    assert db.create_consistent_backup(source, target) == target
    db.verify_sqlite_integrity(target)
    assert not target.with_name(target.name + ".partial").exists()
    with sqlite3.connect(target) as con:
        assert con.execute("SELECT value FROM sample").fetchone()[0] == "kept"


def test_migration_backup_failure_blocks_startup(monkeypatch, tmp_path):
    source = tmp_path / "source.db"
    _create_db(source)
    monkeypatch.setattr(db, "create_consistent_backup", lambda *a, **k: (_ for _ in ()).throw(OSError("disk full")))
    with pytest.raises(RuntimeError, match="Sicherheitsbackup"):
        db._backup_before_schema_migration(source)


def test_diagnostics_bundle_contains_no_database_or_media(monkeypatch, tmp_path):
    diagnostics = tmp_path / "diagnostics"
    diagnostics.mkdir()
    (diagnostics / "fpm.log").write_text("technical log", encoding="utf-8")
    (tmp_path / "fpm.db").write_bytes(b"private-db")
    (tmp_path / "media").mkdir()
    (tmp_path / "media" / "photo.jpg").write_bytes(b"private-media")
    monkeypatch.setattr(log_utils, "diagnostics_dir", lambda: diagnostics)
    monkeypatch.setattr(log_utils, "configure_logging", lambda **k: diagnostics / "fpm.log")
    bundle = log_utils.create_diagnostics_bundle(tmp_path / "support.zip")
    with zipfile.ZipFile(bundle) as archive:
        names = set(archive.namelist())
        assert "logs/fpm.log" in names
        assert "environment.json" in names
        assert not any(name.endswith(".db") or "media" in name for name in names)
        metadata = json.loads(archive.read("environment.json"))
        assert "python" in metadata and "platform" in metadata


def test_release_workflows_are_valid_and_explicitly_unsigned():
    root = Path(__file__).resolve().parents[1]
    release = (root / ".github/workflows/windows-release.yml").read_text(encoding="utf-8")
    check = (root / ".github/workflows/release-check.yml").read_text(encoding="utf-8")
    yaml.safe_load(release)
    yaml.safe_load(check)
    assert "constraints-windows.lock" in release and "constraints-linux.lock" in release
    assert "--require-hashes" in release and "--only-binary=:all:" in release
    assert "softprops/action-gh-release" not in release
    assert "Mark all tagged artifacts as unsigned" in release
    assert "UNSIGNED_RELEASE.txt" in release
    assert "--allow-unsigned" in release
    assert "signtool" not in release.lower()
    assert "WINDOWS_SIGNING_CERT_BASE64" not in release
    assert "LIFEPLANNER_UPDATE_PRIVATE_KEY_B64" not in release
    assert "needs: [build, installer]" in release
    assert "shell: python" not in release
    assert "constraints-windows.lock" in check and "constraints-linux.lock" in check
