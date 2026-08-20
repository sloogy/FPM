"""Central security policy for user-triggered outbound HTTP(S) requests.

All runtime URL fetchers use this module so private, loopback, link-local,
multicast, reserved and otherwise non-public destinations are rejected before
any request and again for every redirect/final URL. Environment proxy settings
are intentionally ignored for these imports to avoid proxy-based SSRF bypasses.
"""
from __future__ import annotations

import http.client
import ipaddress
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

ALLOWED_HTTP_SCHEMES = frozenset({"http", "https"})


class UnsafeRemoteUrlError(ValueError):
    """Raised when a URL is not an approved public HTTP(S) destination."""


@dataclass(frozen=True)
class ValidatedRemoteUrl:
    url: str
    hostname: str
    port: int
    addresses: tuple[str, ...]


def _resolved_public_addresses(host: str, port: int) -> tuple[str, ...]:
    answers = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    if not answers:
        raise UnsafeRemoteUrlError("Zielhost konnte nicht sicher aufgelöst werden.")

    addresses: list[str] = []
    for answer in answers:
        raw_ip = str(answer[4][0]).split("%", 1)[0]
        try:
            ip = ipaddress.ip_address(raw_ip)
        except ValueError as exc:
            raise UnsafeRemoteUrlError("Ungültige Zieladresse.") from exc
        if not ip.is_global:
            raise UnsafeRemoteUrlError(
                f"Nicht-öffentliche Zieladresse ist nicht erlaubt: {ip.compressed}"
            )
        addresses.append(ip.compressed)
    return tuple(dict.fromkeys(addresses))


def validate_public_http_url(url: str) -> ValidatedRemoteUrl:
    """Validate *url* as a credential-free, globally routable HTTP(S) target."""
    raw = str(url or "").strip()
    try:
        parsed = urllib.parse.urlsplit(raw)
    except ValueError as exc:
        raise UnsafeRemoteUrlError("Ungültige URL.") from exc

    scheme = parsed.scheme.lower()
    if scheme not in ALLOWED_HTTP_SCHEMES:
        raise UnsafeRemoteUrlError(
            f"Nur öffentliche http/https-Ziele sind erlaubt, nicht: {scheme or '?'}"
        )
    if not parsed.hostname:
        raise UnsafeRemoteUrlError("URL enthält keinen Zielhost.")
    if parsed.username is not None or parsed.password is not None:
        raise UnsafeRemoteUrlError("Zugangsdaten in URLs sind nicht erlaubt.")

    host = parsed.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith(".localhost"):
        raise UnsafeRemoteUrlError("localhost ist als Downloadziel nicht erlaubt.")

    try:
        port = parsed.port or (443 if scheme == "https" else 80)
    except ValueError as exc:
        raise UnsafeRemoteUrlError("Ungültiger URL-Port.") from exc

    try:
        addresses = _resolved_public_addresses(host, port)
    except OSError as exc:
        raise UnsafeRemoteUrlError("Zielhost konnte nicht sicher aufgelöst werden.") from exc
    return ValidatedRemoteUrl(raw, host, port, addresses)


def is_safe_public_http_url(url: str) -> bool:
    try:
        validate_public_http_url(url)
        return True
    except (UnsafeRemoteUrlError, OSError, TypeError, ValueError):
        return False


def _connected_peer_ip(response) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    """Return the actual TCP peer IP when exposed by urllib/http.client.

    DNS is validated before connecting, but a hostile resolver can change its
    answer between validation and connection (DNS rebinding).  The connected
    socket therefore needs an independent post-connect check.
    """
    try:
        socket_obj = response.fp.raw._sock
        peer = socket_obj.getpeername()
        raw_ip = str(peer[0]).split("%", 1)[0]
        return ipaddress.ip_address(raw_ip)
    except (AttributeError, IndexError, OSError, TypeError, ValueError):
        return None


def validate_connected_peer(response) -> None:
    """Reject a response whose actual TCP peer is not globally routable.

    Real urllib HTTP(S) responses must expose a peer socket; failure to inspect
    it is treated as unsafe.  Lightweight test doubles without a socket remain
    supported, while doubles that expose a peer are checked identically.
    """
    peer_ip = _connected_peer_ip(response)
    if peer_ip is None:
        if isinstance(response, http.client.HTTPResponse):
            raise UnsafeRemoteUrlError(
                "Die tatsächliche Netzwerk-Gegenstelle konnte nicht verifiziert werden."
            )
        return
    if not peer_ip.is_global:
        raise UnsafeRemoteUrlError(
            f"Nicht-öffentliche Netzwerk-Gegenstelle ist nicht erlaubt: {peer_ip.compressed}"
        )


class SafePublicRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Validate every redirect before urllib follows it."""

    max_repeats = 3
    max_redirections = 8

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        try:
            validate_public_http_url(newurl)
        except UnsafeRemoteUrlError as exc:
            raise urllib.error.HTTPError(
                newurl, code, f"Unsicheres Weiterleitungsziel: {exc}", headers, fp
            ) from exc
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def build_public_http_opener() -> urllib.request.OpenerDirector:
    """Build an opener without environment proxies and with redirect validation."""
    return urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        SafePublicRedirectHandler(),
    )


def open_public_http_url(
    url: str,
    *,
    timeout_s: int,
    headers: dict[str, str] | None = None,
    opener: urllib.request.OpenerDirector | None = None,
):
    """Open a validated public URL and revalidate the final response URL."""
    validate_public_http_url(url)
    request = urllib.request.Request(url, headers=headers or {})
    response = (opener or build_public_http_opener()).open(request, timeout=timeout_s)
    try:
        validate_connected_peer(response)
        validate_public_http_url(response.geturl())
    except (UnsafeRemoteUrlError, OSError, ValueError):
        response.close()
        raise
    return response
