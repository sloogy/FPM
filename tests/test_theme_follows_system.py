"""Dem Hell/Dunkel-Wechsel des Betriebssystems folgen.

Warum es diesen Test gibt: Die Einstellung greift an drei Stellen ineinander -
die Abfrage beim Betriebssystem, die Reihenfolge gegenueber dem LifePlanner und
das gespeicherte Designpaar. Faellt eine davon aus, bleibt die Oberflaeche
einfach hell, ohne dass jemand einen Fehler sieht.
"""
from __future__ import annotations

import pytest

from ui import theme_manager as tm
from ui.theme_manager import MODE_DARK, MODE_LIGHT, ThemeManager


@pytest.fixture()
def manager(tmp_path):
    """Eigene Datenbank je Test - die Einstellung liegt in app_settings."""
    from database.db import close_db, init_db

    # init_db schliesst eine offene Datenbank selbst, close_db ist mehrfach
    # gefahrlos aufrufbar - hier braucht es keine Absicherung.
    init_db(tmp_path / "theme.db")
    ThemeManager.reset()
    yield ThemeManager.instance()
    ThemeManager.reset()
    close_db()


def test_standard_ist_aus(manager):
    """Wer sich ein Design ausgesucht hat, soll es behalten."""
    assert manager.follows_system() is False


def test_das_paar_hat_sinnvolle_vorgaben(manager):
    """Ohne eigene Wahl gilt das Auslieferungspaar, nicht der Rueckfall."""
    from ui.theme_manager import INITIAL_DARK_PROFILE, INITIAL_PROFILE

    assert manager.system_pair() == (INITIAL_PROFILE, INITIAL_DARK_PROFILE)


def test_paar_laesst_sich_setzen_und_wirkt(manager, monkeypatch):
    manager.set_system_pair("Solarized - Hell", "Nord - Dunkel")
    manager.set_follows_system(True)
    assert manager.system_pair() == ("Solarized - Hell", "Nord - Dunkel")

    monkeypatch.setattr(tm, "system_mode", lambda: MODE_DARK)
    ThemeManager.reset()
    assert ThemeManager.instance().current_profile().name == "Nord - Dunkel"

    monkeypatch.setattr(tm, "system_mode", lambda: MODE_LIGHT)
    ThemeManager.reset()
    assert ThemeManager.instance().current_profile().name == "Solarized - Hell"


def test_ohne_auskunft_des_systems_bleibt_die_eigene_wahl(manager, monkeypatch):
    """Meldet die Plattform nichts, wird nicht auf gut Glueck hell angenommen."""
    manager.set_current("Dracula - Dunkel")
    manager.set_follows_system(True)
    monkeypatch.setattr(tm, "system_mode", lambda: None)
    ThemeManager.reset()
    assert ThemeManager.instance().current_profile().name == "Dracula - Dunkel"


def test_der_lifeplanner_hat_vorrang(manager, monkeypatch, tmp_path):
    """Im Host gilt dessen Wahl - sonst zoege ein Systemwechsel dagegen."""
    import json

    shared = tmp_path / "theme.json"
    shared.write_text(json.dumps({
        "schema": "lifeplanner.theme.v1",
        "name": "Gruvbox - Hell",
        "modus": "hell",
        "schriftgroesse": 10,
        "farben": {"hintergrund_app": "#fbf1c7"},
    }), encoding="utf-8")
    monkeypatch.setenv("LIFEPLANNER_THEME_FILE", str(shared))

    manager.set_system_pair("Solarized - Hell", "Nord - Dunkel")
    manager.set_follows_system(True)
    monkeypatch.setattr(tm, "system_mode", lambda: MODE_DARK)
    ThemeManager.reset()
    assert ThemeManager.instance().current_profile().name == "Gruvbox - Hell"


def test_system_mode_ohne_qt_anwendung_meldet_nichts():
    """Ohne laufende QApplication gibt es keine Auskunft - und keinen Absturz."""
    from PySide6.QtWidgets import QApplication

    if QApplication.instance() is None:
        assert tm.system_mode() is None
    else:
        assert tm.system_mode() in (None, MODE_LIGHT, MODE_DARK)


# ── Auslieferungszustand ────────────────────────────────────────────────────

def test_neue_installation_bekommt_das_auslieferungsdesign(tmp_path):
    """Eine frische Datenbank startet nicht im Rueckfallprofil."""
    from database.db import close_db, get_session, init_db
    from database.models import AppSettings
    from ui.theme_manager import INITIAL_PROFILE, SETTING_THEME

    init_db(tmp_path / "neu.db")
    session = get_session()
    try:
        assert AppSettings.get(session, SETTING_THEME) == INITIAL_PROFILE
    finally:
        session.close()
    ThemeManager.reset()
    assert ThemeManager.instance().current_profile().name == INITIAL_PROFILE
    close_db()


def test_bestehende_installation_behaelt_ihre_wahl(tmp_path):
    """Ein Update darf niemandem die Farben umstellen."""
    import sqlite3

    from database.db import close_db, get_session, init_db
    from database.models import AppSettings
    from ui.theme_manager import SETTING_THEME

    path = tmp_path / "bestand.db"
    init_db(path)
    close_db()
    # Bestand ohne gespeicherte Wahl - so sehen aeltere Installationen aus.
    with sqlite3.connect(path) as connection:
        connection.execute("DELETE FROM app_settings WHERE key=?", (SETTING_THEME,))

    init_db(path)
    session = get_session()
    try:
        assert AppSettings.get(session, SETTING_THEME) is None
    finally:
        session.close()
    close_db()


def test_auslieferungsdesign_ist_mitgeliefert():
    """Der Name muss ein Profil treffen - sonst startet FPM im Rueckfall."""
    from ui.theme_manager import INITIAL_DARK_PROFILE, INITIAL_PROFILE

    manager = ThemeManager.instance()
    for name in (INITIAL_PROFILE, INITIAL_DARK_PROFILE):
        assert manager.get_profile(name) is not None, name
