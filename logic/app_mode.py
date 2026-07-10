"""UI mode helpers for DAU-friendly navigation.

The app keeps all expert modules available, but the default navigation mode is
intentionally simple: new users see the daily workflow first and can opt into
expert tools when they need them.
"""
from __future__ import annotations

from typing import Literal

APP_MODE_KEY = "ui_navigation_mode"
SIMPLE_MODE = "simple"
EXPERT_MODE = "expert"
VALID_MODES = {SIMPLE_MODE, EXPERT_MODE}

# Pages that should stay visible in simple mode. Expert mode shows every page.
# 0 Dashboard, 1 Pens, 2 Inks, 5 Rotation, 9 Help, 10 Settings.
SIMPLE_PAGES = {0, 1, 2, 5, 9, 10}
EXPERT_ONLY_PAGES = {3, 4, 6, 7, 8, 11, 12, 13}


def normalize_app_mode(mode: str | None) -> Literal["simple", "expert"]:
    mode = (mode or SIMPLE_MODE).strip().lower()
    return EXPERT_MODE if mode == EXPERT_MODE else SIMPLE_MODE


def get_app_mode(default: str = SIMPLE_MODE) -> Literal["simple", "expert"]:
    """Return the persisted UI mode, falling back safely when DB is unavailable."""
    try:
        from database.db import get_session
        from database.models import AppSettings

        session = get_session()
        try:
            return normalize_app_mode(AppSettings.get(session, APP_MODE_KEY, default))
        finally:
            session.close()
    except Exception:
        return normalize_app_mode(default)


def set_app_mode(mode: str) -> Literal["simple", "expert"]:
    """Persist the UI mode and return the normalized value."""
    normalized = normalize_app_mode(mode)
    from database.db import get_session
    from database.models import AppSettings

    session = get_session()
    try:
        AppSettings.set(session, APP_MODE_KEY, normalized)
        return normalized
    finally:
        session.close()


def is_expert_mode(mode: str | None = None) -> bool:
    return normalize_app_mode(mode if mode is not None else get_app_mode()) == EXPERT_MODE


def page_visible(page: int, mode: str | None = None) -> bool:
    """True if a page should be directly visible in the current navigation."""
    normalized = normalize_app_mode(mode if mode is not None else get_app_mode())
    return normalized == EXPERT_MODE or int(page) in SIMPLE_PAGES


def fallback_page(page: int, mode: str | None = None) -> int:
    """Return the requested page or Dashboard when it is hidden in simple mode."""
    return int(page) if page_visible(int(page), mode) else 0
