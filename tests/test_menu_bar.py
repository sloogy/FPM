"""Die Menueleiste des Hauptfensters (Loop 32).

FPM hatte bis dahin keine. Der BudgetManager ist die Design-Vorlage der
Suite, und dort gibt es Datei / Ansicht / Extras / Hilfe. Diese Tests halten
fest, was daran verbindlich ist - nicht die Beschriftungen, sondern der
Aufbau und die Richtlinien, nach denen er entsteht.
"""
from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from i18n.translator import t


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def fenster(qapp, tmp_path):
    from database.db import init_db
    from ui.main_window import MainWindow

    init_db(tmp_path / "menue.db")
    w = MainWindow()
    yield w
    w.close()


def _menues(fenster) -> dict:
    """Die Menues der Leiste, nach Titel.

    Gelesen wird ueber ``fenster._menus`` und nicht ueber
    ``menuBar().actions()[i].menu()``: ``QAction.menu()`` liefert in PySide6
    eine Huelle, die Python gehoert - wird sie als Zwischenwert verworfen,
    nimmt sie das Menue mit. Genau deshalb haelt das Fenster seine Menues
    selbst fest, und genau darauf greift der Test zu.
    """
    return {menu.title(): menu for menu in fenster._menus}


def test_die_vier_menues_der_vorlage_sind_da(fenster):
    """Datei, Ansicht, Extras, Hilfe - in dieser Reihenfolge, wie im
    BudgetManager. Bearbeiten fehlt bewusst: FPM hat keine tabweite
    Bearbeiten-Logik, und ein leeres Menue ist schlimmer als keines."""
    titel = list(_menues(fenster))
    assert titel == [t("menu.file"), t("menu.view"), t("menu.extras"), t("menu.help")]


def test_jedes_menue_hat_eindeutige_zugriffstasten(fenster):
    """Richtlinie 5 der Vorlage: Zwei Eintraege mit demselben ``&``-Buchstaben
    machen die Zugriffstaste wertlos - sie springt dann nur noch hin und her."""
    for titel, menu in _menues(fenster).items():
        tasten = []
        for aktion in menu.actions():
            text = aktion.text()
            if "&" not in text:
                continue
            tasten.append(text.split("&", 1)[1][:1].lower())
        assert len(tasten) == len(set(tasten)), f"{titel}: {tasten}"


def test_auslassungspunkte_nur_wo_ein_dialog_folgt(fenster):
    """Richtlinie 3 und 4: ``…`` steht nur vor Befehlen mit Rueckfrage, und
    nie als drei einzelne Punkte."""
    mit_dialog = {
        t("menu.add_pen"), t("menu.add_ink"), t("menu.fill"),
        t("menu.shortcuts"), t("menu.check_updates"),
    }
    for menu in _menues(fenster).values():
        for aktion in menu.actions():
            text = aktion.text()
            if not text:
                continue
            assert "..." not in text, text
            if text.endswith("…"):
                assert text in mit_dialog, text


def test_ueber_steht_zuletzt(fenster):
    """Richtlinie 6 der Vorlage."""
    hilfe = _menues(fenster)[t("menu.help")]
    sichtbar = [a.text() for a in hilfe.actions() if a.text()]
    assert sichtbar[-1] == t("menu.about")


def test_das_ansichtsmenue_kennt_jede_seite(fenster):
    """Das Menue ist eine zweite Tuer zum selben Raum: Was die Seitenleiste
    anbietet, muss auch hier stehen - sonst haengt es davon ab, welchen Weg
    der Nutzer kennt."""
    from ui.navigation import MODULES

    assert len(fenster._menu_pages.actions()) == len(MODULES)


def test_der_modus_im_menue_folgt_der_seitenleiste(fenster):
    """Der Umschalter sitzt an zwei Stellen. Zeigen sie Verschiedenes, ist
    einer davon falsch - und der Nutzer glaubt dem, den er zuerst sieht."""
    from logic.app_mode import EXPERT_MODE, SIMPLE_MODE

    for modus in (SIMPLE_MODE, EXPERT_MODE):
        fenster.set_navigation_mode(modus)
        aktion = fenster._menu_mode_actions[modus]
        assert aktion.isChecked()
        assert fenster.sidebar.mode() == modus


def test_die_extras_zeigen_dieselben_schnellaktionen_wie_die_werkzeugleiste(fenster):
    """Die Werkzeugleiste ist die schnelle Hand, das Menue die auffindbare.
    Zwei verschiedene Sammlungen waeren zwei Wahrheiten."""
    extras = _menues(fenster)[t("menu.extras")]
    texte = {a.text() for a in extras.actions() if a.text()}
    for schluessel in ("menu.add_pen", "menu.add_ink", "menu.fill",
                       "menu.cleaned", "menu.suggest_rotation"):
        assert t(schluessel) in texte


def test_die_menueleiste_ersetzt_die_werkzeugleiste_nicht(fenster):
    """Wer FPM kennt, soll nach dem Update nicht umlernen muessen."""
    from PySide6.QtWidgets import QToolBar

    leisten = fenster.findChildren(QToolBar)
    assert any(lb.objectName() == "mainToolbar" for lb in leisten)
    assert fenster.sidebar is not None


def test_zugriffstasten_sind_in_jeder_sprache_eindeutig():
    """Richtlinie 5 gilt nicht nur auf Deutsch.

    Uebersetzt wird Wort fuer Wort, das ``&`` wandert dabei mit - und landet
    leicht auf einem Buchstaben, den im selben Menue schon jemand hat. Der
    Konflikt faellt sonst erst dem Nutzer auf, der die Sprache benutzt.
    """
    import json
    from pathlib import Path

    gruppen = {
        "leiste": ["file", "view", "extras", "help"],
        "file": ["settings", "open_data_folder", "exit"],
        "view": ["pages", "mode", "fullscreen"],
        "extras": ["add_pen", "add_ink", "fill", "cleaned",
                   "suggest_rotation", "search"],
        "help": ["manual", "context_help", "tour", "shortcuts",
                 "check_updates", "about"],
    }
    wurzel = Path(__file__).resolve().parents[1] / "i18n"
    for sprache in ("de", "en", "fr"):
        menu = json.loads((wurzel / f"{sprache}.json").read_text(encoding="utf-8"))["menu"]
        for name, schluessel in gruppen.items():
            fehlend = [k for k in schluessel if "&" not in menu[k]]
            assert not fehlend, f"{sprache}/{name} ohne Zugriffstaste: {fehlend}"
            tasten = [menu[k].split("&", 1)[1][:1].lower() for k in schluessel]
            assert len(tasten) == len(set(tasten)), f"{sprache}/{name}: {tasten}"


def test_das_menue_waechst_mit_der_profilschrift():
    """Loop 8 hat das fuer den BudgetManager durchgesetzt, Loop 9 die
    abgestuften Radien. Eine Menueleiste mit festen Pixelwerten waere in
    beidem ein Rueckschritt - und faellt sofort auf, weil sie als einziger
    Teil der Oberflaeche nicht mitwaechst."""
    from ui.styles import get_stylesheet

    klein = get_stylesheet(1.0)
    gross = get_stylesheet(1.6)

    def polster(css: str) -> str:
        i = css.index("QMenuBar::item {")
        return css[i:css.index("}", i)]

    assert polster(klein) != polster(gross)
    assert "border-radius" in polster(klein)
