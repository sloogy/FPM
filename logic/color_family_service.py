"""Zentrale Normalisierung von Farbfamilien für Import, UI und Rotation."""
from __future__ import annotations

COLOR_FAMILY_ALIASES = {
    "blau": "blue", "blue": "blue", "navy": "blue", "dunkelblau": "blue", "royal blue": "blue", "königsblau": "blue", "koenigsblau": "blue",
    "rot": "red", "red": "red", "weinrot": "red", "burgundy": "red", "bordeaux": "red",
    "grün": "green", "gruen": "green", "green": "green", "waldgrün": "green", "forest green": "green",
    "petrol": "teal", "teal": "teal", "türkisblau": "teal", "tuerkisblau": "teal",
    "türkis": "turquoise", "tuerkis": "turquoise", "turquoise": "turquoise", "cyan": "turquoise",
    "lila": "purple", "violett": "purple", "purple": "purple", "violet": "purple", "magenta": "purple",
    "braun": "brown", "brown": "brown", "sepia": "brown",
    "schwarz": "black", "black": "black",
    "grau": "grey", "gray": "grey", "grey": "grey",
    "orange": "orange", "gelb": "yellow", "yellow": "yellow", "pink": "pink", "rosa": "pink",
}

VALID_COLOR_FAMILIES = {"blue", "black", "red", "green", "purple", "brown", "orange", "grey", "teal", "turquoise", "yellow", "pink", "other"}

def normalize_color_family(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if not text:
        return None
    if text in COLOR_FAMILY_ALIASES:
        return COLOR_FAMILY_ALIASES[text]
    if text in VALID_COLOR_FAMILIES:
        return text
    compact = text.replace("-", " ").replace("_", " ")
    if compact in COLOR_FAMILY_ALIASES:
        return COLOR_FAMILY_ALIASES[compact]
    for alias, family in sorted(COLOR_FAMILY_ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
        if alias in compact:
            return family
    return "other"
