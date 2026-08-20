"""Designprofil des LifePlanner-Hosts.

Der Host legt das zentral gewaehlte Profil im Format ``lifeplanner.theme.v1``
ab und nennt den Pfad in ``LIFEPLANNER_THEME_FILE``. Ohne Host ist die Variable
leer und alles hier ist ein No-Op - der Standalone-Betrieb bleibt unveraendert.

FPMs Stylesheet fuehrt seine Farben als Literale. Statt es vollstaendig auf
Tokens umzubauen, ordnet ``PALETTE_ROLES`` jedem Literal die Rolle zu, die es
im Stylesheet tatsaechlich hat, und ersetzt es durch den Wert des Hostprofils.
Das deckt Hauptfenster, Seitenleiste, Tabellen, Eingaben und Schriftgroessen
ab. Inline-Styles einzelner Widgets bleiben unberuehrt.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

log = logging.getLogger(__name__)

THEME_ENV_FILE = "LIFEPLANNER_THEME_FILE"
THEME_SCHEMA = "lifeplanner.theme.v1"
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")

# Der BudgetManager - und damit der Host - fuehrt 10 als Standardschriftgroesse.
# FPM skaliert stattdessen ueber einen Faktor; 10 bedeutet also "unveraendert".
_REFERENCE_FONT_SIZE = 10.0

# Literal im FPM-Stylesheet -> Rolle im Hostprofil.
PALETTE_ROLES: dict[str, str] = {
    "#f0f3f7": "hintergrund_app",
    "#ffffff": "hintergrund_panel",
    "#f8fafc": "hintergrund_panel",
    "#2c3e50": "text",
    "#1e2a38": "text",
    "#5f6f72": "text_gedimmt",
    "#94a3b8": "text_gedimmt",
    "#3498db": "akzent",
    "#2563eb": "akzent",
    "#d5dce6": "tabelle_gitter",
    "#cbd5e1": "tabelle_gitter",
    "#edf0f5": "tabelle_alt",
    "#edf1f7": "tabelle_alt",
    "#e5edf5": "tabelle_alt",
    "#f7f9fc": "tabelle_alt",
    "#0b1220": "hintergrund_seitenleiste",
    "#18212d": "hintergrund_seitenleiste",
    "#1f2937": "hover_hintergrund",
    "#e8f1ff": "hover_hintergrund",
    "#d6e9f8": "hover_hintergrund",
    "#1d4ed8": "auswahl_hintergrund",
}


def load_host_theme() -> dict[str, Any] | None:
    """Hostprofil oder ``None`` im Standalone-Betrieb."""
    path = (os.environ.get(THEME_ENV_FILE) or "").strip()
    if not path or not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("Hostdesign nicht lesbar (%s): %s", path, exc)
        return None
    if not isinstance(data, dict) or data.get("schema") != THEME_SCHEMA:
        return None
    return data if str(data.get("name", "")).strip() else None


def host_scale_factor(theme: dict[str, Any] | None) -> float:
    """Schriftgroesse des Profils als FPM-Skalierungsfaktor."""
    if not theme:
        return 1.0
    try:
        size = float(theme.get("schriftgroesse") or _REFERENCE_FONT_SIZE)
    except (TypeError, ValueError):
        return 1.0
    if size <= 0:
        return 1.0
    return max(0.85, min(1.50, size / _REFERENCE_FONT_SIZE))


def recolor(css: str, theme: dict[str, Any] | None) -> str:
    """Ersetzt die Stylesheet-Literale durch die Farben des Hostprofils."""
    if not theme:
        return css
    colors = theme.get("farben")
    if not isinstance(colors, dict):
        return css
    for literal, role in PALETTE_ROLES.items():
        value = str(colors.get(role, "") or "").strip()
        if not _HEX.fullmatch(value):
            continue
        css = re.sub(re.escape(literal), value, css, flags=re.IGNORECASE)
    return css


def is_dark(theme: dict[str, Any] | None) -> bool:
    return bool(theme) and str(theme.get("modus", "")).strip().lower() == "dunkel"
