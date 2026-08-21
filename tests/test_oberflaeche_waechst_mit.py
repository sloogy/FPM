"""Die Oberflaeche waechst mit der eingestellten Schriftgroesse.

Warum es das braucht: Die Schriftgroesse steht im Designprofil. Feste
Pixelwerte im Stylesheet setzen sich darueber hinweg - wer die Schrift zur
besseren Lesbarkeit hochstellt, bekommt dann groesseren Text in unveraendert
engen Feldern. Das faellt in keinem Funktionstest auf, sondern erst am Bild.

Alle vier Programme der Suite fuehren diesen Test unter demselben Namen.
"""

from __future__ import annotations

import re

import pytest

from ui.styles import _build_stylesheet
from ui.theme_manager import DEFAULT_FONT_SIZE


def _stylesheet(schriftgroesse: int) -> str:
    """Das Stylesheet zu einer Schriftgroesse.

    Hier wird bewusst die reine Aufbaufunktion genommen: ``get_stylesheet``
    holt das Profil selbst und liefert bei jedem Aufruf ein frisches Objekt,
    an dem sich eine gesetzte Schriftgroesse nicht festhalten liesse.
    """
    faktor = max(0.85, min(1.50, schriftgroesse / float(DEFAULT_FONT_SIZE)))
    return _build_stylesheet(faktor)


def _groessen(css: str, eigenschaft: str) -> list[int]:
    return [int(x) for x in re.findall(rf"{eigenschaft}:\s*(\d+)px", css)]


@pytest.mark.parametrize("eigenschaft", ["font-size", "min-height", "border-radius"])
def test_die_masse_wachsen_mit_der_schrift(eigenschaft):
    klein = _groessen(_stylesheet(8), eigenschaft)
    gross = _groessen(_stylesheet(16), eigenschaft)
    assert klein and len(klein) == len(gross), f"{eigenschaft} nicht vergleichbar"
    # Nicht jede einzelne Angabe muss wachsen - ein 1px-Rand bleibt 1px -,
    # aber in der Summe muss die Oberflaeche deutlich groesser werden.
    assert sum(gross) > sum(klein) * 1.3, (
        f"{eigenschaft} waechst kaum mit: {sum(klein)} -> {sum(gross)}"
    )


def test_bei_standardgroesse_bleibt_alles_wie_bisher():
    """Der Auslieferungszustand darf sich durch die Skalierung nicht aendern."""
    css = _stylesheet(10)
    assert "border-radius: 6px" in css
    assert "border-radius: 4px" in css


def test_die_radien_sind_abgestuft():
    """Nach dem Vorbild des BudgetManagers: je groesser die Flaeche, desto
    runder die Ecke. Ein einziger Wert liesse Karten so eckig wirken wie
    Eingabefelder."""
    css = _stylesheet(10)
    radien = set(_groessen(css, "border-radius"))
    assert {4, 6, 8}.issubset(radien), sorted(radien)
