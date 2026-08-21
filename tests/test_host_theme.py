"""Zentrales Designprofil des LifePlanner-Hosts."""
import json

import pytest

from ui.host_theme import host_scale_factor, load_host_theme, recolor
from ui.styles import get_stylesheet
from ui.theme_manager import ThemeManager


@pytest.fixture(autouse=True)
def _fresh_theme():
    """Das aktive Profil ist ein Singleton - sonst faerbt ein Test den naechsten."""
    ThemeManager.reset()
    yield
    ThemeManager.reset()


# Bewusst ein Name, den FPM nicht selbst mitliefert: Kennt FPM das Profil,
# hat die eigene, vollstaendige Fassung Vorrang - dann pruefte der Test die
# lokale Datei statt der Uebergabe vom Host.
def _profile(tmp_path, name="Host-Design", modus="dunkel", size=10, **farben):
    path = tmp_path / "theme.json"
    path.write_text(json.dumps({
        "schema": "lifeplanner.theme.v1",
        "name": name,
        "modus": modus,
        "schriftgroesse": size,
        "farben": {"hintergrund_app": "#2e3440", "text": "#d8dee9",
                   "akzent": "#88c0d0", **farben},
    }), encoding="utf-8")
    return path


def test_without_host_the_local_profile_applies(monkeypatch):
    """Ohne Host gilt das eigene Profil - frueher blieb FPM hier fest hell.

    Genau daran lag es, dass ein dunkles Design im eigenstaendigen Betrieb
    gar nicht erst zur Verfuegung stand.
    """
    from ui.theme_manager import DEFAULT_PROFILE, ThemeManager

    monkeypatch.delenv("LIFEPLANNER_THEME_FILE", raising=False)
    ThemeManager.reset()
    css = get_stylesheet()
    assert load_host_theme() is None
    # Das Standardprofil kommt aus dem gemeinsamen Katalog, nicht mehr aus dem
    # eingebauten Rueckfall - der greift nur noch, wenn keine Datei da ist.
    standard = ThemeManager.instance().get_profile(DEFAULT_PROFILE)
    assert standard is not None
    assert standard.color("hintergrund_app") in css
    assert standard.color("text") in css
    assert standard.color("akzent") in css
    # Keine Farbe mehr, die kein Profil kennt.
    assert "#3498db" not in css


def test_host_profile_recolours_main_window_and_accent(monkeypatch, tmp_path):
    monkeypatch.setenv("LIFEPLANNER_THEME_FILE", str(_profile(tmp_path)))
    css = get_stylesheet()
    assert "#2e3440" in css and "#d8dee9" in css and "#88c0d0" in css
    assert "#f0f3f7" not in css and "#3498db" not in css


def test_a_design_fpm_ships_itself_wins_over_the_host_excerpt(monkeypatch, tmp_path):
    """Der Host liefert einen Auszug, FPM das vollstaendige Profil.

    Deshalb hat die eigene Fassung Vorrang - sonst faellt alles, was der Host
    nicht mitschickt, auf das eingebaute Standardprofil zurueck.
    """
    from ui.theme_manager import ThemeManager

    monkeypatch.setenv("LIFEPLANNER_THEME_FILE",
                       str(_profile(tmp_path, name="Nord - Dunkel")))
    ThemeManager.reset()
    profile = ThemeManager.instance().current_profile()
    assert profile.name == "Nord - Dunkel"
    local = ThemeManager.instance().get_profile("Nord - Dunkel")
    assert profile.color("text") == local.color("text")
    # Und zwar vollstaendig: auch Rollen, die der Host gar nicht mitschickt.
    assert profile.color("karte_rand") == local.color("karte_rand")


def test_font_size_drives_the_scale_factor():
    assert host_scale_factor(None) == 1.0
    assert host_scale_factor({"schriftgroesse": 10}) == 1.0
    assert host_scale_factor({"schriftgroesse": 12}) == 1.2
    # Ausserhalb des zulaessigen Bereichs wird geklemmt, nicht verworfen.
    assert host_scale_factor({"schriftgroesse": 30}) == 1.50
    assert host_scale_factor({"schriftgroesse": 0}) == 1.0
    assert host_scale_factor({"schriftgroesse": "kaputt"}) == 1.0


def test_broken_or_foreign_files_are_ignored(monkeypatch, tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{kein json", encoding="utf-8")
    monkeypatch.setenv("LIFEPLANNER_THEME_FILE", str(bad))
    assert load_host_theme() is None

    foreign = tmp_path / "foreign.json"
    foreign.write_text(json.dumps({"schema": "etwas.anderes", "name": "X"}), encoding="utf-8")
    monkeypatch.setenv("LIFEPLANNER_THEME_FILE", str(foreign))
    assert load_host_theme() is None

    monkeypatch.setenv("LIFEPLANNER_THEME_FILE", str(tmp_path / "gibt-es-nicht.json"))
    assert load_host_theme() is None


def test_recolor_skips_invalid_colour_values():
    """Ein uebergebenes Profil mit unbrauchbaren Farben aendert nichts."""
    css = "background: #f0f3f7;"
    assert recolor(css, {"farben": {"hintergrund_app": "rot"}}) == css
    assert recolor(css, {"farben": {}}) == css


def test_recolor_without_argument_uses_the_active_profile(monkeypatch):
    """Ohne uebergebenes Profil gilt das aktive - dafuer ist die Funktion da.

    Die Inline-Stylesheets der Widgets laufen genau so hier durch.
    """
    from ui.theme_manager import DEFAULT_PROFILE, ThemeManager

    monkeypatch.delenv("LIFEPLANNER_THEME_FILE", raising=False)
    ThemeManager.reset()
    expected = ThemeManager.instance().get_profile(DEFAULT_PROFILE).color("hintergrund_app")
    assert recolor("background: #f0f3f7;") == f"background: {expected};"


def test_recolor_is_single_pass_and_never_chains():
    """Eine Zielfarbe darf nicht erneut als Literal ersetzt werden."""
    # hintergrund_app -> #ffffff, und #ffffff ist selbst ein Literal.
    theme = {"farben": {"hintergrund_app": "#ffffff", "hintergrund_panel": "#222222"}}
    assert recolor("background: #f0f3f7;", theme) == "background: #ffffff;"
    # Das echte #ffffff wird trotzdem korrekt ersetzt.
    assert recolor("card: #ffffff;", theme) == "card: #222222;"


def test_semantic_colours_keep_their_meaning():
    """Erfolg, Gefahr und Warnung tragen Bedeutung, nicht die Rolle einer Flaeche.

    Sie folgen dem Profil trotzdem - aber ueber die Bedeutungsrollen. Sonst
    waere ein sattes Rot auf dunklem Grund kaum zu lesen.
    """
    from ui.host_theme import PALETTE_ROLES, SEMANTIC_ROLES

    for semantic in ("#27ae60", "#e74c3c", "#c0392b", "#f39c12", "#d35400", "#8e44ad"):
        assert semantic not in PALETTE_ROLES, "Bedeutungsfarbe darf keine Flaechenrolle sein"
        assert semantic in SEMANTIC_ROLES
    assert SEMANTIC_ROLES["#e74c3c"] == "gefahr"
    assert SEMANTIC_ROLES["#27ae60"] == "erfolg"


def test_inline_widget_styles_follow_the_host_profile(monkeypatch, tmp_path):
    from PySide6.QtWidgets import QApplication, QPushButton

    import ui.host_theme as ht

    monkeypatch.setenv("LIFEPLANNER_THEME_FILE", str(_profile(tmp_path)))
    monkeypatch.setattr(ht, "_PATCHED", False)
    app = QApplication.instance() or QApplication([])
    assert ht.install_inline_theme() is True
    button = QPushButton("x")
    button.setStyleSheet("background:#3498db;color:white;")
    # #3498db ist der Akzent des Profils. Der Patch bleibt danach installiert,
    # ist ohne gesetzte Umgebungsvariable aber ein No-Op.
    assert "#88c0d0" in button.styleSheet()
    assert "#3498db" not in button.styleSheet()
    # Und "white" wird jetzt ebenfalls getroffen - frueher blieb die Schrift
    # weiss, auch wenn die Flaeche darunter hell wurde.
    assert "white" not in button.styleSheet()
