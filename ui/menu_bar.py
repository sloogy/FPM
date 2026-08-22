"""Menüleiste des Hauptfensters – Aufbau nach der BudgetManager-Vorlage.

FPM hatte bis Loop 32 gar keine Menüleiste: Alles lief über die Seitenleiste
und eine Werkzeugleiste mit sieben Knöpfen. Das ist für sich genommen
bedienbar, macht die Suite aber uneinheitlich – der BudgetManager ist die
Design-Vorlage, und dort gibt es Datei / Bearbeiten / Ansicht / Extras /
Hilfe. Wer zwischen beiden wechselt, sucht in FPM an einer Stelle, die es
nicht gibt.

Übernommen sind auch die Richtlinien, die der BudgetManager in
``views/help_menu.py`` festhält (GNOME HIG, Windows App Design, Apple HIG –
die drei sind sich in diesen Punkten einig):

1. **Kurz halten.** Selten Gebrauchtes wandert in Untermenüs.
2. **Gruppieren statt aufzählen.** Trennlinien bilden Sinnabschnitte.
3. **Auslassungspunkte nur bei Rückfrage.** ``…`` steht ausschließlich vor
   Befehlen, die einen Dialog öffnen. Wer nur die Seite wechselt, bekommt
   keine.
4. **Ein einheitliches Auslassungszeichen** – ``…``, nie ``...``.
5. **Eindeutige Zugriffstasten.** Jeder Eintrag bekommt ein ``&`` auf einem
   innerhalb seines Menüs eindeutigen Buchstaben.
6. **„Über" steht zuletzt**, „Nach Updates suchen" gehört ins Hilfe-Menü.
7. **Klartext statt Jargon.**

Die Menüleiste ersetzt nichts, sie ergänzt. Werkzeugleiste und Seitenleiste
bleiben, wo sie sind: Ein Nutzer, der FPM kennt, soll nach dem Update nicht
umlernen müssen.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import QDialogButtonBox, QLabel, QMenuBar, QVBoxLayout

from i18n.translator import t
from logic.app_mode import EXPERT_MODE, SIMPLE_MODE
from ui.navigation import MODULES, PAGE_SHORTCUTS

#: Seite der Einstellungen und der Hilfe. Beide sind in FPM normale Seiten im
#: Stapel, keine Dialoge - darum kein ``…`` an ihren Menüeinträgen.
SEITE_HILFE = 9
SEITE_EINSTELLUNGEN = 10


def _eintrag(menu, fenster, text: str, callback, *, kuerzel: str = "", tip: str = ""):
    """Ein Menüeintrag mit Zugriffstaste, Kürzel und Statuszeilentext."""
    aktion = QAction(text, fenster)
    if kuerzel:
        aktion.setShortcut(QKeySequence(kuerzel))
        # Ohne diesen Kontext feuert das Kürzel nur, solange das Menü offen
        # ist - also nie.
        aktion.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
    if tip:
        aktion.setStatusTip(tip)
    aktion.triggered.connect(callback)
    menu.addAction(aktion)
    return aktion


def build_menu_bar(fenster) -> QMenuBar:
    """Baut die Menüleiste des Hauptfensters auf und gibt sie zurück.

    Leiste und Menüs werden am Fenster festgehalten. Ohne das räumt die
    Speicherbereinigung die Python-Hüllen weg, sobald der letzte Verweis
    fällt - und nimmt die C++-Objekte mit. Sichtbar wird das erst unter
    pytest, wo häufiger aufgeräumt wird als im laufenden Programm: Das Menü
    ist dann noch da, aber leer.
    """
    leiste = fenster.menuBar()
    leiste.clear()
    fenster._menu_bar = leiste
    fenster._menus = [
        _datei_menu(leiste, fenster),
        _ansicht_menu(leiste, fenster),
        _extras_menu(leiste, fenster),
        _hilfe_menu(leiste, fenster),
    ]
    return leiste


def _datei_menu(leiste: QMenuBar, fenster):
    menu = leiste.addMenu(t("menu.file"))
    _eintrag(menu, fenster, t("menu.settings"),
             lambda: fenster._navigate(SEITE_EINSTELLUNGEN),
             tip=t("menu.settings_tip"))
    _eintrag(menu, fenster, t("menu.open_data_folder"),
             lambda: _datenordner_oeffnen(fenster),
             tip=t("menu.open_data_folder_tip"))
    menu.addSeparator()
    _eintrag(menu, fenster, t("menu.exit"), fenster.close,
             kuerzel="Ctrl+Q", tip=t("menu.exit_tip"))
    return menu


def _ansicht_menu(leiste: QMenuBar, fenster):
    menu = leiste.addMenu(t("menu.view"))

    seiten = menu.addMenu(t("menu.pages"))
    # Dieselbe Reihenfolge wie in der Seitenleiste: Das Menü ist eine zweite
    # Tür zum selben Raum, keine eigene Ordnung.
    for modul in MODULES.values():
        nummer = modul["page"]
        _eintrag(
            seiten, fenster,
            f"{modul['icon']}  {t(modul['title_key'])}",
            lambda _=False, p=nummer: fenster._navigate(p),
            kuerzel=PAGE_SHORTCUTS.get(nummer, ""),
        )

    menu.addSeparator()

    modus = menu.addMenu(t("menu.mode"))
    gruppe = QActionGroup(fenster)
    gruppe.setExclusive(True)
    fenster._menu_mode_actions = {}
    for kennung, schluessel in ((SIMPLE_MODE, "menu.mode_simple"),
                                (EXPERT_MODE, "menu.mode_expert")):
        aktion = QAction(t(schluessel), fenster)
        aktion.setCheckable(True)
        aktion.triggered.connect(
            lambda _=False, m=kennung: fenster.set_navigation_mode(m)
        )
        gruppe.addAction(aktion)
        modus.addAction(aktion)
        fenster._menu_mode_actions[kennung] = aktion

    menu.addSeparator()

    vollbild = QAction(t("menu.fullscreen"), fenster)
    vollbild.setCheckable(True)
    vollbild.setShortcut(QKeySequence("F11"))
    vollbild.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
    vollbild.setStatusTip(t("menu.fullscreen_tip"))
    vollbild.triggered.connect(lambda an: _vollbild(fenster, an))
    menu.addAction(vollbild)
    fenster._menu_fullscreen_action = vollbild
    fenster._menu_pages = seiten
    fenster._menu_mode = modus
    return menu


def _extras_menu(leiste: QMenuBar, fenster):
    """Dieselben Schnellaktionen wie in der Werkzeugleiste.

    Bewusst dieselben und nicht andere: Die Werkzeugleiste ist die schnelle
    Hand, das Menü die auffindbare - wer den Knopf nicht deutet, findet den
    Befehl hier ausgeschrieben, mit Kürzel daneben.
    """
    menu = leiste.addMenu(t("menu.extras"))
    _eintrag(menu, fenster, t("menu.add_pen"),
             lambda: fenster._run_page_action(1, "_add"))
    _eintrag(menu, fenster, t("menu.add_ink"),
             lambda: fenster._run_page_action(2, "_add"))
    menu.addSeparator()
    _eintrag(menu, fenster, t("menu.fill"),
             lambda: fenster._run_page_action(1, "_load_ink"))
    _eintrag(menu, fenster, t("menu.cleaned"),
             lambda: fenster._run_page_action(1, "_mark_cleaned"))
    _eintrag(menu, fenster, t("menu.suggest_rotation"),
             lambda: fenster._run_page_action(5, "generate_suggestions"))
    menu.addSeparator()
    _eintrag(menu, fenster, t("menu.search"), fenster._shortcut_find,
             kuerzel="Ctrl+F", tip=t("menu.search_tip"))
    return menu


def _hilfe_menu(leiste: QMenuBar, fenster):
    menu = leiste.addMenu(t("menu.help"))
    # Nachschlagen
    _eintrag(menu, fenster, t("menu.manual"),
             lambda: fenster._navigate(SEITE_HILFE),
             tip=t("menu.manual_tip"))
    _eintrag(menu, fenster, t("menu.context_help"), fenster._open_context_help,
             kuerzel="F1", tip=t("menu.context_help_tip"))
    menu.addSeparator()
    # Lernen
    _eintrag(menu, fenster, t("menu.tour"), fenster.start_tour,
             tip=t("menu.tour_tip"))
    _eintrag(menu, fenster, t("menu.shortcuts"),
             lambda: _kuerzel_dialog(fenster))
    menu.addSeparator()
    # Version
    _eintrag(menu, fenster, t("menu.check_updates"),
             lambda: _update_dialog(fenster))
    menu.addSeparator()
    # Über steht zuletzt
    _eintrag(menu, fenster, t("menu.about"),
             lambda: _ueber_zeigen(fenster))
    return menu


def _vollbild(fenster, an: bool) -> None:
    if an:
        fenster.showFullScreen()
    else:
        fenster.showNormal()


def _datenordner_oeffnen(fenster) -> None:
    """Öffnet den Ordner der Datenbank im Dateimanager des Systems."""
    from database.db import get_db_path
    from ui.common import open_in_file_manager

    open_in_file_manager(fenster, get_db_path().parent)


def _update_dialog(fenster) -> None:
    from ui.update_dialog import UpdateDialog

    UpdateDialog(fenster).exec()


def _ueber_zeigen(fenster) -> None:
    """Führt auf die Über-Seite der Einstellungen.

    Bewusst kein eigener Dialog: Version, Technik und Datenpfad stehen dort
    schon. Ein zweiter Ort mit denselben Angaben ist ein zweiter Ort, der
    veralten kann.
    """
    fenster._navigate(SEITE_EINSTELLUNGEN)
    widget = fenster._ensure_widget(SEITE_EINSTELLUNGEN)
    zeigen = getattr(widget, "show_about_page", None)
    if callable(zeigen):
        zeigen()


def _kuerzel_dialog(fenster) -> None:
    """Listet die Tastenkürzel auf - die globalen und die der Seiten."""
    from ui.common import ResponsiveDialog

    zeilen = [
        (t("menu.shortcuts_new"), QKeySequence(QKeySequence.StandardKey.New).toString()),
        (t("menu.shortcuts_find"), "Ctrl+F"),
        (t("menu.shortcuts_context_help"), "F1"),
        (t("menu.shortcuts_fullscreen"), "F11"),
        (t("menu.shortcuts_quit"), "Ctrl+Q"),
    ]
    for modul in MODULES.values():
        kuerzel = PAGE_SHORTCUTS.get(modul["page"], "")
        if kuerzel:
            zeilen.append((t(modul["title_key"]), kuerzel))

    dialog = ResponsiveDialog(fenster)
    dialog.setWindowTitle(t("menu.shortcuts_title"))
    layout = QVBoxLayout(dialog)
    for name, kuerzel in zeilen:
        layout.addWidget(QLabel(f"<b>{kuerzel}</b> — {name}"))
    knoepfe = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    knoepfe.rejected.connect(dialog.reject)
    knoepfe.accepted.connect(dialog.accept)
    layout.addWidget(knoepfe)
    dialog.exec()


def sync_menu_state(fenster) -> None:
    """Hält Häkchen im Ansicht-Menü mit dem tatsächlichen Zustand gleich.

    Ohne das zeigt das Menü einen Modus an, den die Seitenleiste längst
    verlassen hat - der Umschalter sitzt dort ebenfalls.
    """
    aktionen = getattr(fenster, "_menu_mode_actions", None)
    if aktionen:
        aktuell = fenster.sidebar.mode()
        for kennung, aktion in aktionen.items():
            aktion.setChecked(kennung == aktuell)
    vollbild = getattr(fenster, "_menu_fullscreen_action", None)
    if vollbild is not None:
        vollbild.setChecked(fenster.isFullScreen())


__all__ = ["build_menu_bar", "sync_menu_state"]
