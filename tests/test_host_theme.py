"""Zentrales Designprofil des LifePlanner-Hosts."""
import json

from ui.host_theme import host_scale_factor, load_host_theme, recolor
from ui.styles import get_stylesheet


def _profile(tmp_path, name="Nord - Dunkel", modus="dunkel", size=10, **farben):
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


def test_without_host_the_stylesheet_is_unchanged(monkeypatch):
    monkeypatch.delenv("LIFEPLANNER_THEME_FILE", raising=False)
    css = get_stylesheet()
    assert load_host_theme() is None
    # Die bisherigen Literale muessen im Standalone-Betrieb erhalten bleiben.
    assert "#f0f3f7" in css and "#2c3e50" in css and "#3498db" in css


def test_host_profile_recolours_main_window_and_accent(monkeypatch, tmp_path):
    monkeypatch.setenv("LIFEPLANNER_THEME_FILE", str(_profile(tmp_path)))
    css = get_stylesheet()
    assert "#2e3440" in css and "#d8dee9" in css and "#88c0d0" in css
    assert "#f0f3f7" not in css and "#3498db" not in css


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
    css = "background: #f0f3f7;"
    assert recolor(css, {"farben": {"hintergrund_app": "rot"}}) == css
    assert recolor(css, {"farben": {}}) == css
    assert recolor(css, None) == css


def test_recolor_is_single_pass_and_never_chains():
    """Eine Zielfarbe darf nicht erneut als Literal ersetzt werden."""
    # hintergrund_app -> #ffffff, und #ffffff ist selbst ein Literal.
    theme = {"farben": {"hintergrund_app": "#ffffff", "hintergrund_panel": "#222222"}}
    assert recolor("background: #f0f3f7;", theme) == "background: #ffffff;"
    # Das echte #ffffff wird trotzdem korrekt ersetzt.
    assert recolor("card: #ffffff;", theme) == "card: #222222;"


def test_semantic_colours_stay_untouched():
    """Erfolg, Gefahr und Warnung tragen Bedeutung, nicht die Rolle einer Flaeche."""
    from ui.host_theme import PALETTE_ROLES

    for semantic in ("#27ae60", "#e74c3c", "#c0392b", "#f39c12", "#d35400", "#8e44ad"):
        assert semantic not in PALETTE_ROLES


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
