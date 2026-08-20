"""Backward-compatible image URL security exports.

The authoritative implementation lives in :mod:`logic.network_security` and is
used by every active network path, not only by the image dialog.
"""
from __future__ import annotations

from logic.network_security import (
    SafePublicRedirectHandler,
    is_safe_public_http_url,
)


def _is_safe_remote_image_url(url: str) -> bool:
    return is_safe_public_http_url(url)


class _SafeImageRedirectHandler(SafePublicRedirectHandler):
    pass
