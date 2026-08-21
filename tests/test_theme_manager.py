"""Designprofile in FPM.

Bis v1.0.3 hatte FPM kein eigenes Theme: Farben standen als Literale im
Stylesheet und in rund 150 Inline-Aufrufen. Ein dunkles Profil ergab weisse
Karten und graue Schrift auf grauem Grund. Diese Tests halten fest, dass
Farben aus dem Profil kommen - und zwar vollstaendig.
"""
from __future__ import annotations

import json
import re

import pytest

from ui.theme_manager import (
    BUILTIN_PROFILES,
    COLOR_KEYS,
    DEFAULT_PROFILE,
    MODE_DARK,
    ThemeManager,
    ThemeProfile,
    host_theme_as_profile_data,
    validate_profile_data,
)

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


@pytest.fixture(autouse=True)
def _fresh_theme():
    ThemeManager.reset()
    yield
    ThemeManager.reset()


def test_beide_standardprofile_kennen_jede_rolle():
    """Eine fehlende Rolle faellt sonst erst als graues Widget auf."""
    for name, data in BUILTIN_PROFILES.items():
        missing = [key for key in COLOR_KEYS if key not in data]
        assert not missing, f"{name}: {missing}"
        for key in COLOR_KEYS:
            assert HEX.match(data[key]), f"{name}/{key} ist keine Farbe: {data[key]!r}"


def test_mitgelieferte_profile_sind_gueltig():
    manager = ThemeManager.instance()
    assert not manager.get_load_errors(), manager.get_load_errors()
    # Mehr als nur die beiden eingebauten.
    assert len(manager.available_profiles()) > len(BUILTIN_PROFILES)


@pytest.mark.parametrize("name", sorted(ThemeManager().available_profiles()))
def test_jedes_profil_liefert_jede_rolle(name):
    """Auch ein knappes Profil muss jede Rolle beantworten - ueber den Rueckfall."""
    profile = ThemeManager.instance().get_profile(name)
    assert profile is not None
    for key in COLOR_KEYS:
        assert HEX.match(profile.color(key)), f"{name}/{key}"


def test_fehlende_rolle_faellt_auf_die_passende_helligkeit_zurueck():
    """Ein dunkles Profil darf nie eine helle Rueckfallfarbe bekommen."""
    sparse = ThemeProfile("Knapp", {"modus": MODE_DARK})
    assert sparse.color("hintergrund_app") == BUILTIN_PROFILES["Standard - Dunkel"]["hintergrund_app"]
    assert sparse.color("text") == BUILTIN_PROFILES["Standard - Dunkel"]["text"]


def test_kaputtes_profil_wird_uebersprungen_nicht_verschwiegen(tmp_path, monkeypatch):
    good = tmp_path / "gut.json"
    good.write_text(json.dumps({"name": "Gut", "modus": "hell", "text": "#111111"}),
                    encoding="utf-8")
    bad = tmp_path / "kaputt.json"
    bad.write_text(json.dumps({"name": "Kaputt", "modus": "lila"}), encoding="utf-8")

    monkeypatch.setattr(ThemeManager, "bundled_dir", staticmethod(lambda: tmp_path))
    ThemeManager.reset()
    manager = ThemeManager.instance()
    assert "Gut" in manager.available_profiles()
    assert "Kaputt" not in manager.available_profiles()
    assert any("Kaputt" in name for name, _path, _msg in manager.get_load_errors())


def test_validierung_weist_unbrauchbare_werte_ab():
    assert validate_profile_data({"modus": "hell"})[0] is True
    assert validate_profile_data({"modus": "gruen"})[0] is False
    assert validate_profile_data({"modus": "hell", "schriftgroesse": 99})[0] is False
    assert validate_profile_data({"modus": "hell", "text": "#12345"})[0] is False


def test_schriftgroesse_wirkt_als_skalierung():
    assert ThemeProfile("A", {"schriftgroesse": 10}).scale == 1.0
    assert ThemeProfile("B", {"schriftgroesse": 12}).scale == 1.2
    # Ausserhalb des Bereichs wird geklemmt, nicht verworfen.
    assert ThemeProfile("C", {"schriftgroesse": 40}).scale == 1.5
    assert ThemeProfile("D", {"schriftgroesse": "kaputt"}).scale == 1.0


def test_hostprofil_wird_zu_einem_vollwertigen_profil():
    data = {"schema": "lifeplanner.theme.v1", "name": "X", "modus": "dunkel",
            "schriftgroesse": 12,
            "farben": {"hintergrund_app": "#101010", "unbekannt": "#ffffff",
                       "text": "kaputt"}}
    payload = host_theme_as_profile_data(data)
    assert payload["modus"] == MODE_DARK
    assert payload["schriftgroesse"] == 12
    assert payload["hintergrund_app"] == "#101010"
    # Weder unbekannte Rollen noch unbrauchbare Werte werden uebernommen.
    assert "unbekannt" not in payload
    assert "text" not in payload
    # Was fehlt, kommt aus dem dunklen Standard - nicht aus dem hellen.
    profile = ThemeProfile("X", payload)
    assert profile.color("text") == BUILTIN_PROFILES["Standard - Dunkel"]["text"]


def test_programmstandard_ist_immer_aufloesbar():
    """Der Eintrag 'Programmstandard' im Dropdown muss ein Profil ergeben."""
    manager = ThemeManager.instance()
    assert DEFAULT_PROFILE in manager.available_profiles()
    assert manager.get_profile(DEFAULT_PROFILE) is not None


def test_unbekanntes_profil_wird_abgelehnt():
    with pytest.raises(ValueError):
        ThemeManager.instance().set_current("Gibt es nicht")


# ── Das Stylesheet ───────────────────────────────────────────────────────────

def _luminance(hex_color: str) -> float:
    """Wahrgenommene Helligkeit 0..1 - grob, aber fuer hell/dunkel genug."""
    value = hex_color.lstrip("#")
    r, g, b = (int(value[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


# Die Farben, die vor der Umstellung fest im Stylesheet standen. Keine davon
# darf wieder auftauchen, ausser das aktive Profil fuehrt sie selbst.
FRUEHERE_LITERALE = ("#f0f3f7", "#2c3e50", "#3498db", "#edf0f5", "#edf1f7",
                     "#4a5568", "#bdc3c7", "#95a5a6", "#7f8c8d", "#e8f1ff",
                     "#d6e9f8", "#2980b9", "#1f6391", "#219a52", "#c0392b",
                     "#d68910", "#6c7a7d")


def _palette(profile) -> set[str]:
    """Alle Farben, die aus diesem Profil entstehen koennen.

    Neben den Rollen selbst die daraus abgeleiteten Hover- und Drucktoene -
    sie sind Profilfarben, nur aufgehellt oder abgedunkelt.
    """
    from ui import theme

    values = {theme.sidebar_panel().lower(), theme.sidebar_panel_hover().lower()}
    for key in COLOR_KEYS:
        base = profile.color(key)
        values.add(base.lower())
        for factor in (0.35, 0.6, 0.65, 0.78, 0.8, 0.88, 1.15, 1.28, 1.3,
                       1.35, 1.4, 1.5, 1.6, 1.85, 2.0):
            values.add(theme.shade(base, factor).lower())
    return values


def test_stylesheet_fuehrt_keine_festen_literale_mehr(monkeypatch):
    """Genau diese Literale kannte kein Profil - sie blieben deshalb hell."""
    from ui.styles import get_stylesheet

    monkeypatch.delenv("LIFEPLANNER_THEME_FILE", raising=False)
    ThemeManager.reset()
    profile = ThemeManager.instance().current_profile()
    own = _palette(profile)
    css = get_stylesheet().lower()
    stale = [literal for literal in FRUEHERE_LITERALE
             if literal in css and literal not in own]
    assert not stale, f"feste Literale zurueck im Stylesheet: {stale}"


def test_jede_farbe_im_stylesheet_stammt_aus_dem_profil(monkeypatch):
    """Kein Wert darf mehr an einem Profil vorbei ins Stylesheet gelangen."""
    from ui.styles import get_stylesheet

    monkeypatch.delenv("LIFEPLANNER_THEME_FILE", raising=False)
    ThemeManager.reset()
    profile = ThemeManager.instance().current_profile()
    allowed = _palette(profile)
    found = {value.lower() for value in re.findall(r"#[0-9a-fA-F]{6}", get_stylesheet())}
    assert not found - allowed, f"profilfremde Farben: {sorted(found - allowed)}"


def test_stylesheet_setzt_keine_feste_schriftfarbe(monkeypatch):
    """'color: white' war der Grund fuer weisse Schrift auf hellem Grund."""
    from ui.styles import get_stylesheet

    monkeypatch.delenv("LIFEPLANNER_THEME_FILE", raising=False)
    ThemeManager.reset()
    css = get_stylesheet().lower()
    for literal in ("color: white", "color:white", "color: black", "color:black"):
        assert literal not in css


def test_dunkles_profil_laesst_keine_helle_flaeche_zurueck(monkeypatch, tmp_path):
    """Der Fall aus dem Fehlerbild: weisse Karte auf dunklem Grund.

    Geprueft werden die Flaechen, nicht die Schrift: Weisse Schrift auf einem
    blauen Knopf ist richtig, eine weisse Flaeche im dunklen Profil nicht.
    """
    from ui.styles import get_stylesheet

    path = tmp_path / "theme.json"
    path.write_text(json.dumps({
        "schema": "lifeplanner.theme.v1", "name": "Mitternacht", "modus": "dunkel",
        "schriftgroesse": 10,
        "farben": {"hintergrund_app": "#111827", "hintergrund_panel": "#1f2937",
                   "text": "#e5e7eb", "akzent": "#60a5fa"},
    }), encoding="utf-8")
    monkeypatch.setenv("LIFEPLANNER_THEME_FILE", str(path))
    ThemeManager.reset()

    css = get_stylesheet()
    assert "#111827" in css and "#1f2937" in css and "#e5e7eb" in css

    # Die grossen Flaechen - nicht die Bedeutungsfarben: Ein gruener
    # Erfolgsknopf ist auch im dunklen Profil hell, und das ist richtig.
    flaechen = ("hintergrund_app", "hintergrund_panel", "karte_hintergrund",
                "eingabe_hintergrund", "tabelle_hintergrund", "tabelle_alt",
                "tabelle_header", "hintergrund_seitenleiste")
    profile = ThemeManager.instance().current_profile()
    assert profile.is_dark
    for key in flaechen:
        value = profile.color(key)
        assert _luminance(value) < 0.4, f"{key} ist hell: {value}"
        assert value.lower() in css.lower(), f"{key} kommt im Stylesheet nicht vor"


def test_helles_profil_laesst_keine_dunkle_flaeche_im_inhalt(monkeypatch):
    """Gegenprobe. Die Seitenleiste ist bewusst dunkel und bleibt ausgenommen."""
    from ui.styles import get_stylesheet

    monkeypatch.delenv("LIFEPLANNER_THEME_FILE", raising=False)
    ThemeManager.reset()
    css = get_stylesheet()
    # Bloecke der Seitenleiste und des Tooltips herausnehmen - sie sind auch
    # in hellen Profilen dunkel, das ist Absicht.
    blocks = [block for block in css.split("}")
              if not re.search(r"sidebar|navbutton|modetoggle|tooltip", block, re.I)]
    backgrounds = re.findall(r"background(?:-color)?\s*:\s*(#[0-9a-fA-F]{6})",
                             "}".join(blocks))
    dunkel = sorted({value for value in backgrounds if _luminance(value) < 0.25})
    assert not dunkel, f"dunkle Flaechen im hellen Profil: {dunkel}"


def test_profile_liegen_im_paket():
    """Ohne diesen Eintrag blieben im gebauten Programm nur zwei Profile."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    spec = (root / "FPM.spec").read_text(encoding="utf-8")
    assert '"ui/profiles"' in spec
    assert list((root / "ui" / "profiles").glob("*.json")), "keine Profile vorhanden"
