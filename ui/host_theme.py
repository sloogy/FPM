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
    # Weitere Grautoene aus den Widget-Inlinestyles.
    "#64748b": "text_gedimmt",
    "#7f8c8d": "text_gedimmt",
    "#34495e": "hintergrund_seitenleiste",
}

# Bewusst NICHT zugeordnet: #27ae60, #e74c3c, #c0392b, #f39c12, #d35400 und
# #8e44ad. Diese Farben tragen Bedeutung - Erfolg, Gefahr, Warnung, Kategorie -
# und nicht die Rolle einer Flaeche. Sie an ein Designprofil zu koppeln wuerde
# eine Loeschen-Schaltflaeche gruen faerben, wenn das Profil es so vorgibt.


def load_host_theme() -> dict[str, Any] | None:
    """Hostprofil oder ``None`` im Standalone-Betrieb."""
    path = (os.environ.get(THEME_ENV_FILE) or "").strip()
    if not path or not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        # Reine Diagnosemeldung, kein sichtbarer UI-Text - daher nicht uebersetzt.
        log.warning("Host theme file is not readable (%s): %s", path, exc)
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


def build_color_map(theme: dict[str, Any] | None) -> dict[str, str]:
    """Literal -> Zielfarbe fuer genau dieses Profil."""
    if not theme:
        return {}
    colors = theme.get("farben")
    if not isinstance(colors, dict):
        return {}
    mapping: dict[str, str] = {}
    for literal, role in PALETTE_ROLES.items():
        value = str(colors.get(role, "") or "").strip()
        if _HEX.fullmatch(value):
            mapping[literal.lower()] = value
    return mapping


def recolor(css: str, theme: dict[str, Any] | None) -> str:
    """Ersetzt die Stylesheet-Literale durch die Farben des Hostprofils.

    Ein einziger Durchgang ueber alle Literale gleichzeitig. Nacheinander
    ausgefuehrte Einzelersetzungen wuerden ketten: waere die Zielfarbe des
    einen Literals selbst ein Literal, ersetzte der naechste Durchlauf sie
    gleich weiter.
    """
    if not css:
        return css
    mapping = build_color_map(theme)
    if not mapping:
        return css
    pattern = re.compile("|".join(re.escape(k) for k in mapping), re.IGNORECASE)
    return pattern.sub(lambda m: mapping[m.group(0).lower()], css)


_PATCHED = False


def install_inline_theme() -> bool:
    """Laesst auch Inline-Stylesheets einzelner Widgets dem Hostprofil folgen.

    FPM setzt an rund 150 Stellen ``setStyleSheet`` mit eigenen Farbliteralen.
    Diese lokalen Stylesheets schlagen das globale, sodass die betroffenen
    Widgets sonst hell blieben, waehrend der Rest dem Profil folgt. Statt jeden
    Aufruf einzeln umzuschreiben, laeuft hier jeder Widget-Stylesheet durch
    dieselbe Farbzuordnung wie das globale.

    Ohne Hostprofil passiert nichts. Nur einmal wirksam.
    """
    global _PATCHED
    if _PATCHED or not load_host_theme():
        return False
    from PySide6.QtWidgets import QWidget

    original = QWidget.setStyleSheet

    def themed_set_stylesheet(self, sheet):  # noqa: ANN001 - Qt-Signatur
        return original(self, recolor(sheet, load_host_theme()))

    QWidget.setStyleSheet = themed_set_stylesheet
    _PATCHED = True
    return True


def is_dark(theme: dict[str, Any] | None) -> bool:
    return bool(theme) and str(theme.get("modus", "")).strip().lower() == "dunkel"
