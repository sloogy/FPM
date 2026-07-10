from __future__ import annotations

"""Zentrale App-Metadaten.

Eine einzige Versionsquelle fuer UI, Installer, Portable-ZIP und Updater.
"""

APP_NAME = "FountainPen Manager"
APP_VERSION = "0.2.87"
APP_RELEASE_DATE = "8. Juli 2026"
APP_BUILD = "release-audit-media-hardening"
APP_DESCRIPTION = (
    "Release-Audit: Medien-Import kann keine Datensaetze mehr zerstoeren; "
    "Recherche oeffnet die ersten beiden Suchstufen."
)
APP_TITLE = f"✒ {APP_NAME} v{APP_VERSION}"
ORG_NAME = "FountainPen Community"


def app_window_title() -> str:
    return f"✒ {APP_NAME} v{APP_VERSION}"


def app_about_title() -> str:
    return f"Über {APP_NAME} v{APP_VERSION}"


def app_version_label() -> str:
    return f"{APP_VERSION} ({APP_RELEASE_DATE})"
