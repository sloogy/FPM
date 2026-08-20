"""Farben und Schaltflaechenstile aus dem aktiven Designprofil.

Frueher standen hier feste Hex-Werte. Das war der Grund, warum FPM in einem
dunklen Profil weisse Karten und graue Schrift auf grauem Grund zeigte: Die
Literale kannten das Profil nicht. Jetzt fragt jede Funktion das aktive Profil
(``ui/theme_manager.py``), und ein Profilwechsel wirkt ueberall.

Die Namen bleiben die der frueheren Konstanten, damit der Aufrufer sich nicht
umgewoehnen muss - aus ``btn_primary()`` wird ``btn_primary()``.
"""
from __future__ import annotations

from ui.theme_manager import ThemeManager


def profile():
    return ThemeManager.instance().current_profile()


def color(role: str) -> str:
    """Farbe einer Rolle im aktiven Profil."""
    return profile().color(role)


def is_dark() -> bool:
    return profile().is_dark


def scale() -> float:
    """Schriftgroesse des Profils als Skalierungsfaktor."""
    return profile().scale


def shade(hex_color: str, factor: float) -> str:
    """Hellt eine Farbe auf (>1) oder dunkelt sie ab (<1).

    Damit entstehen Hover- und Druckzustaende aus der Profilfarbe selbst.
    Fest eingetragene dunklere Toene waeren im dunklen Profil falsch herum:
    dort muss ein Hover heller werden, nicht dunkler.
    """
    value = str(hex_color or "").strip().lstrip("#")
    if len(value) != 6:
        return hex_color
    try:
        parts = [int(value[i:i + 2], 16) for i in (0, 2, 4)]
    except ValueError:
        return hex_color
    return "#" + "".join(f"{max(0, min(255, round(c * factor))):02x}" for c in parts)


def hover(role: str) -> str:
    """Hoverton einer Rolle - im dunklen Profil heller, im hellen dunkler."""
    return shade(color(role), 1.15 if is_dark() else 0.88)


def pressed(role: str) -> str:
    return shade(color(role), 1.28 if is_dark() else 0.78)


def sidebar_panel() -> str:
    """Die abgesetzte Flaeche in der Seitenleiste.

    Eine eigene Rolle waere schoener, wuerde aber jedes vorhandene Profil um
    einen Schluessel erweitern. Stattdessen wird sie aus der Seitenleiste
    abgeleitet - benannt, damit sie nicht als verschachtelte Rechnung an
    mehreren Stellen entsteht.
    """
    return shade(color("hintergrund_seitenleiste"), 1.35 if is_dark() else 1.6)


def sidebar_panel_hover() -> str:
    return shade(sidebar_panel(), 1.4)


def _button(background: str, foreground: str, *, padding: str = "7px 16px",
            bold: bool = True) -> str:
    weight = "font-weight:bold;" if bold else ""
    return (f"background:{background};color:{foreground};border:none;"
            f"padding:{padding};border-radius:5px;{weight}")


# ── Schaltflaechen ───────────────────────────────────────────────────────────
def btn_primary() -> str:
    return _button(color("akzent"), color("akzent_text"))


def btn_success() -> str:
    return _button(color("erfolg"), color("erfolg_text"), padding="7px 18px")


def btn_danger() -> str:
    return _button(color("gefahr"), color("gefahr_text"))


def btn_secondary() -> str:
    return _button(color("hintergrund_seitenleiste"), color("seitenleiste_text"),
                   padding="7px 14px")


def btn_muted() -> str:
    return _button(color("gedaempft"), color("gedaempft_text"), bold=False)


def btn_accent() -> str:
    return _button(color("bereich_aktivitaet"), color("akzent_text"), padding="7px 14px")


# ── Flaechen und Texte ───────────────────────────────────────────────────────
def card() -> str:
    """Karte: Flaeche, Rand, Textfarbe - alles aus dem Profil."""
    return (f"background:{color('karte_hintergrund')};color:{color('text')};"
            f"border:1px solid {color('karte_rand')};border-radius:8px;")


def hint_text() -> str:
    """Erklaerender Fliesstext unter einer Ueberschrift.

    Ohne gesetzten Hintergrund: Ein eigener Hintergrund auf einem Label ergab
    im dunklen Profil den schwarzen Balken quer durch die helle Karte.
    """
    return f"color:{color('text_gedimmt')};background:transparent;border:none;"


def section_title(role: str = "akzent") -> str:
    """Ueberschrift eines Bereichs; ``role`` waehlt die Bedeutungsfarbe."""
    return f"color:{color(role)};background:transparent;border:none;font-weight:bold;"


def value_text() -> str:
    """Grosse Kennzahl auf einer Karte."""
    return f"color:{color('text')};background:transparent;border:none;font-weight:bold;"


def link_button(role: str = "akzent") -> str:
    """Flache Schaltflaeche mit Rand in der Bedeutungsfarbe."""
    return (f"background:transparent;color:{color(role)};"
            f"border:1px solid {color(role)};border-radius:5px;padding:4px 10px;")


# Alte Schreibweise als Grossbuchstaben-Konstante. Sie liefert den Wert des
# aktiven Profils zum Zeitpunkt des Zugriffs; Module, die sie beim Import
# binden, sehen einen Profilwechsel erst nach ihrem Neuaufbau.
_ALIASES = {
    "btn_primary()": btn_primary,
    "btn_success()": btn_success,
    "btn_danger()": btn_danger,
    "btn_secondary()": btn_secondary,
    "btn_muted()": btn_muted,
    "btn_accent()": btn_accent,
}


def __getattr__(name: str) -> str:
    if name in _ALIASES:
        return _ALIASES[name]()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
