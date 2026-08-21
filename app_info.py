from __future__ import annotations

"""Zentrale App-Metadaten.

Eine einzige Versionsquelle fuer UI, Installer, Portable-ZIP und Updater.
"""

APP_NAME = "FountainPen Manager"
APP_VERSION = "1.0.4"
APP_RELEASE_DATE = "20. August 2026"
APP_BUILD = "enterprise-lifeplanner-pipeline"
APP_DESCRIPTION = (
    "Enterprise-gehärteter Stand mit zentralem SSRF-Schutz, sicher abbrechbaren "
    "Downloads, atomaren SQLite-Sicherheitsbackups, Produktionsdiagnostik und "
    "fail-closed Cross-Platform-Release-Pipeline inklusive signierter LifePlanner-Module."
)
APP_TITLE = f"✒ {APP_NAME} v{APP_VERSION}"
ORG_NAME = "FountainPen Community"


def app_window_title() -> str:
    return f"✒ {APP_NAME} v{APP_VERSION}"


def app_about_title() -> str:
    return f"Über {APP_NAME} v{APP_VERSION}"


def app_version_label() -> str:
    return f"{APP_VERSION} ({APP_RELEASE_DATE})"
