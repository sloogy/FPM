"""Farbersetzung fuer die noch nicht migrierten Inline-Stylesheets.

FPM setzt an rund 150 Stellen ``setStyleSheet`` mit eigenen Farbliteralen.
Solche lokalen Stylesheets schlagen das globale - die betroffenen Widgets
blieben also hell, waehrend der Rest dem Profil folgt. Genau das war der Grund
fuer weisse Karten und weisse Schrift auf hellem Grund im dunklen Profil.

Bis jede Stelle auf ``ui.theme`` umgestellt ist, laeuft hier jeder
Widget-Stylesheet durch eine Zuordnung: Literal -> Rolle -> Farbe des aktiven
Profils. Anders als frueher haengt das **nicht** mehr am LifePlanner-Host -
es wirkt auch im eigenstaendigen Betrieb, weil FPM jetzt selbst Profile hat.

``load_host_theme`` bleibt bestehen: der Host liefert weiterhin das gemeinsame
Profil, das der ThemeManager als Quelle bevorzugt.
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
    "#7f8c8d": "gedaempft",
    "#34495e": "hintergrund_seitenleiste",
    # Ohne diese blieben Flaechen und Schriften hell: "white" ist kein
    # Hexliteral und wurde vom alten Muster nie erfasst.
    "white": "hintergrund_panel",
    "#fff": "hintergrund_panel",
    "#bdc3c7": "rand",
    "#95a5a6": "text_gedimmt",
    "#eee": "tabelle_alt",
    "#555": "text_gedimmt",
    "#475569": "tabelle_header_text",
    "#4a5568": "tabelle_header_text",
    "#2980b9": "akzent_hover",
    "#eff6ff": "hover_hintergrund",
    "#dbeafe": "auswahl_hintergrund",
    "#f1f5f9": "hintergrund_app",
    "#e2e8f0": "rand",
    "#111827": "hintergrund_seitenleiste",
    "#020617": "hintergrund_seitenleiste",
}

# Literale, die ihre Bedeutung tragen und deshalb NICHT auf Flaechenrollen
# zeigen, sondern auf die Bedeutungsrollen des Profils. Im dunklen Profil sind
# deren Werte aufgehellt, damit sie lesbar bleiben.
SEMANTIC_ROLES: dict[str, str] = {
    "#27ae60": "erfolg",
    "#219a52": "erfolg",
    "#e74c3c": "gefahr",
    "#c0392b": "gefahr",
    "#f39c12": "warnung",
    "#e67e22": "warnung",
    "#d68910": "warnung",
    "#8e44ad": "bereich_sammlung",
    "#d35400": "bereich_rotation",
    "#16a085": "bereich_aktivitaet",
}

# Bedeutungsfarben werden ueber SEMANTIC_ROLES gefuehrt, nicht ueber
# Flaechenrollen: Eine Loeschen-Schaltflaeche bleibt rot, aber im dunklen
# Profil in dessen hellerem Rot - sonst waere sie kaum zu lesen.


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


def build_color_map(theme: dict[str, Any] | None = None) -> dict[str, str]:
    """Literal -> Farbe des aktiven Profils.

    ``theme`` ist nur noch fuer Aufrufer da, die ausdruecklich ein rohes
    Hostprofil abbilden wollen; ohne Argument gilt das aktive Profil.
    """
    if theme is not None:
        colors = theme.get("farben")
        if not isinstance(colors, dict):
            return {}
        lookup = lambda role: str(colors.get(role, "") or "").strip()  # noqa: E731
    else:
        from ui.theme_manager import ThemeManager
        profile = ThemeManager.instance().current_profile()
        lookup = profile.color

    mapping: dict[str, str] = {}
    for source in (PALETTE_ROLES, SEMANTIC_ROLES):
        for literal, role in source.items():
            value = lookup(role)
            if _HEX.fullmatch(value or ""):
                mapping[literal.lower()] = value
    return mapping


def recolor(css: str, theme: dict[str, Any] | None = None) -> str:
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
    # Laengste Literale zuerst, sonst schluckt "#fff" den Anfang von "#ffffff".
    # Wortgrenzen halten "white" von "whitesmoke" fern.
    keys = sorted(mapping, key=len, reverse=True)
    pattern = re.compile("|".join(rf"\b{re.escape(k)}\b" if k.isalpha() else re.escape(k)
                                 for k in keys), re.IGNORECASE)
    return pattern.sub(lambda m: mapping[m.group(0).lower()], css)


_PATCHED = False


def install_inline_theme() -> bool:
    """Laesst auch Inline-Stylesheets einzelner Widgets dem Hostprofil folgen.

    FPM setzt an rund 150 Stellen ``setStyleSheet`` mit eigenen Farbliteralen.
    Diese lokalen Stylesheets schlagen das globale, sodass die betroffenen
    Widgets sonst hell blieben, waehrend der Rest dem Profil folgt. Statt jeden
    Aufruf einzeln umzuschreiben, laeuft hier jeder Widget-Stylesheet durch
    dieselbe Farbzuordnung wie das globale.

    Nur einmal wirksam. Eine Uebergangsloesung: Jede Stelle, die auf
    ``ui.theme`` umgestellt ist, braucht sie nicht mehr.
    """
    global _PATCHED
    if _PATCHED:
        return False
    from PySide6.QtWidgets import QWidget

    original = QWidget.setStyleSheet

    def themed_set_stylesheet(self, sheet):  # noqa: ANN001 - Qt-Signatur
        return original(self, recolor(sheet))

    QWidget.setStyleSheet = themed_set_stylesheet
    _PATCHED = True
    return True


def is_dark(theme: dict[str, Any] | None) -> bool:
    return bool(theme) and str(theme.get("modus", "")).strip().lower() == "dunkel"
