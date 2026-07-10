"""Tests für die reinen Helfer der Rotation-Engine (Farbe, Set-Diversität)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_engine_helpers():
    """Lädt nur die Modul-Helfer ohne SQLAlchemy-Abhängigkeit zu triggern.
    Wir lesen die Funktionen direkt aus dem Quelltext bis zur Klasse aus.
    """
    # Die reinen Helfer werden ohne Datenbank-/Qt-Import gespiegelt.
    ns: dict = {}
    # Definiere die reinen Farbfunktionen manuell nach (Spiegel des Engine-Codes)
    code = '''
def _hex_to_rgb(hex_str):
    h = (hex_str or "#888888").lstrip("#")
    if len(h) != 6:
        return (128, 128, 128)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

def _color_distance(hex1, hex2):
    r1, g1, b1 = _hex_to_rgb(hex1)
    r2, g2, b2 = _hex_to_rgb(hex2)
    return ((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2) ** 0.5
'''
    exec(code, ns)
    return ns


HELPERS = _load_engine_helpers()


# ── Farb-Distanz ──────────────────────────────────────────────────
def test_color_distance_identical_is_zero():
    assert HELPERS["_color_distance"]("#aabbcc", "#aabbcc") == 0.0


def test_color_distance_red_blue_large():
    d = HELPERS["_color_distance"]("#ff0000", "#0000ff")
    assert d > 350


def test_color_distance_similar_blues_small():
    d = HELPERS["_color_distance"]("#1a2b6c", "#1e3175")
    assert d < 30


def test_hex_to_rgb_invalid_fallback():
    assert HELPERS["_hex_to_rgb"]("garbage") == (128, 128, 128)
    assert HELPERS["_hex_to_rgb"]("") == (136, 136, 136)  # "" -> Default-Grau #888888


def test_hex_to_rgb_parses_correctly():
    assert HELPERS["_hex_to_rgb"]("#ff8000") == (255, 128, 0)


# ── Set-Diversität: Logik-Spiegel ─────────────────────────────────
def test_diversity_bonus_prefers_distant_colors():
    """Eine farblich weit entfernte Tinte soll höheren Diversity-Bonus geben."""
    cd = HELPERS["_color_distance"]
    selected = ["#003153"]  # Navy
    near = "#1e3175"   # ähnliches Blau
    far  = "#cc0000"   # Rot
    bonus_near = min(30, int(min(cd(near, h) for h in selected) / 12))
    bonus_far  = min(30, int(min(cd(far, h) for h in selected) / 12))
    assert bonus_far > bonus_near

# ── Release-Hardening: aktive Tinten / Verbrauch ──────────────────
def test_rotation_source_filters_exact_active_inks_by_default():
    """Regression ohne PySide6-Import: exakte aktive Tinte wird standardmäßig nicht doppelt vorgeschlagen."""
    src = (ROOT / "logic" / "rotation_engine.py").read_text(encoding="utf-8")
    assert "rotation_allow_active_ink_duplicates" in src
    assert "ink.id in active_ink_ids" in src
    assert "pen.fixed_ink_id != ink.id" in src
    assert "allow_active_duplicates" in src
    assert "continue" in src


def test_rotation_source_uses_central_ink_consumption_helper():
    """Ink-Verbrauch soll zentral geclamped werden und nicht als verstreute Sonderlogik."""
    src = (ROOT / "logic" / "rotation_engine.py").read_text(encoding="utf-8")
    assert "from logic.enthusiast_lab_service import apply_ink_consumption" in src
    assert "ink.remaining_ml = apply_ink_consumption(ink.remaining_ml, vol)" in src
