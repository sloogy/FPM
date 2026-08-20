"""Security regression guards added during the v0.3.00 enterprise audit."""
from __future__ import annotations

import socket

# v0.3.02: SSRF-Logik liegt Qt-frei in logic/ und ist damit auch in
# der Sandbox direkt testbar (ui.pen_widget re-exportiert weiterhin).
from logic.image_url_security import _is_safe_remote_image_url


def test_remote_image_url_rejects_local_and_non_http_targets(monkeypatch):
    assert not _is_safe_remote_image_url("file:///etc/passwd")
    assert not _is_safe_remote_image_url("http://localhost/image.png")
    assert not _is_safe_remote_image_url("http://user:pass@example.com/image.png")

    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 80))],
    )
    assert not _is_safe_remote_image_url("http://example.test/image.png")


def test_remote_image_url_accepts_only_globally_routable_addresses(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))],
    )
    assert _is_safe_remote_image_url("https://example.com/image.png")

    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.5", 443)),
        ],
    )
    assert not _is_safe_remote_image_url("https://mixed.example/image.png")
