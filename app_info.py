from __future__ import annotations

"""Zentrale App-Metadaten.

Eine einzige Versionsquelle fuer UI, Installer, Portable-ZIP und Updater.
"""

APP_NAME = "FountainPen Manager"
APP_VERSION = "0.2.88"
APP_RELEASE_DATE = "10. Juli 2026"
APP_BUILD = "locale-currency-hardening"
APP_DESCRIPTION = (
    "Einheitliche, app-gesteuerte Zahlen- und Währungsformate mit sicherer "
    "Komma-/Punkt-Eingabe sowie gehärteter Rotation, Führung und Datensicherung."
)
APP_TITLE = f"✒ {APP_NAME} v{APP_VERSION}"
ORG_NAME = "FountainPen Community"


def app_window_title() -> str:
    return f"✒ {APP_NAME} v{APP_VERSION}"


def app_about_title() -> str:
    return f"Über {APP_NAME} v{APP_VERSION}"


def app_version_label() -> str:
    return f"{APP_VERSION} ({APP_RELEASE_DATE})"
