"""Hauptfenster – Calibre-artiges Layout mit fester Modul-Leiste und Lazy Loading.

v0.2.10:
- Widgets werden nicht mehr alle beim Start erzeugt. Das reduziert PySide/Qt-Crashrisiken
  und macht den Start deutlich robuster.
v0.2.25:
- AppEventBus: Widgets subscriben sich bei Erstellung und refreshen sich gegenseitig.
- App-Tour: erscheint beim ersten Start wenn DB leer ist; klassischer Wizard bleibt als Fallback verfügbar.
"""
from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QStackedWidget, QToolBar, QLineEdit

from ui.navigation import CalibreSidebar, PAGE_SHORTCUTS
from logic.app_mode import EXPERT_MODE, fallback_page, page_visible
from app_info import APP_TITLE
from ui.ui_scale import scale_px
from i18n.translator import t


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self._apply_responsive_window_geometry()
        self._widgets: dict[int, QWidget | None] = {}
        self._setup_ui()
        self._setup_shortcuts()
        self._watch_system_color_scheme()

    def _watch_system_color_scheme(self) -> None:
        """Auf den Hell/Dunkel-Wechsel des Betriebssystems reagieren.

        Ohne diese Verbindung wuerde die Einstellung "dem System folgen" erst
        beim naechsten Start greifen - und genau das ist die Situation, in der
        sie niemandem hilft.
        """
        app = QApplication.instance()
        if app is None:
            return
        hints = app.styleHints()
        signal = getattr(hints, "colorSchemeChanged", None)
        if signal is None:  # Qt aelter als 6.5
            return
        signal.connect(self._system_color_scheme_changed)

    def _system_color_scheme_changed(self, _scheme) -> None:
        from ui.theme_manager import ThemeManager

        manager = ThemeManager.instance()
        if not manager.follows_system() or manager.follows_shared_and_hosted():
            return
        ThemeManager.reset()
        self._restyle()

    def _restyle(self) -> None:
        """Stylesheet neu setzen und die Seiten neu aufbauen."""
        from ui.settings_widget import _restyle_application

        _restyle_application()

    def _apply_responsive_window_geometry(self) -> None:
        """Setzt eine nutzbare Fenstergröße innerhalb der Arbeitsfläche."""
        app = QApplication.instance()
        screen = self.screen() or (app.primaryScreen() if app else None)
        if screen is None:
            self.setMinimumSize(900, 580)
            self.resize(1200, 760)
            return

        available = screen.availableGeometry()
        margin = scale_px(32)
        max_width = max(760, available.width() - margin)
        max_height = max(520, available.height() - margin)

        minimum_width = min(scale_px(980), max_width)
        minimum_height = min(scale_px(620), max_height)
        self.setMinimumSize(minimum_width, minimum_height)

        target_width = min(scale_px(1360), round(available.width() * 0.88), max_width)
        target_height = min(scale_px(820), round(available.height() * 0.88), max_height)
        self.resize(max(minimum_width, target_width), max(minimum_height, target_height))

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if getattr(self, "_screen_hook_installed", False):
            return
        handle = self.windowHandle()
        if handle is not None:
            handle.screenChanged.connect(lambda _screen: QTimer.singleShot(0, self._apply_responsive_window_geometry))
            self._screen_hook_installed = True

    def _setup_shortcuts(self):
        """Usability 3.6: Standard-Shortcuts für schnelle Dateneingabe.

        Ctrl+N → neuer Eintrag auf der aktiven Seite, Ctrl+F → Suche,
        Ctrl+1…9 → Seitennavigation. Entf wird pro Seitentabelle registriert
        (siehe _ensure_widget), damit Textfelder ihre Entf-Taste behalten.
        """
        from PySide6.QtGui import QKeySequence, QShortcut
        QShortcut(QKeySequence.StandardKey.New, self, activated=self._shortcut_add)
        QShortcut(QKeySequence.StandardKey.Find, self, activated=self._shortcut_find)
        for page, shortcut in PAGE_SHORTCUTS.items():
            QShortcut(QKeySequence(shortcut), self, activated=lambda p=page: self._navigate(p))

    def _shortcut_add(self):
        widget = self._widgets.get(self._stack.currentIndex())
        if widget is not None and hasattr(widget, "_add"):
            widget._add()

    def _shortcut_find(self):
        self.global_search.setFocus()
        self.global_search.selectAll()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.sidebar = CalibreSidebar()
        self.sidebar.pageSelected.connect(self._navigate)
        self.sidebar.modeChanged.connect(self._navigation_mode_changed)
        root.addWidget(self.sidebar)

        self._stack = QStackedWidget()
        root.addWidget(self._stack, 1)

        # Platzhalterseiten; echte Module werden erst beim ersten Öffnen erzeugt.
        for i in range(14):
            ph = QWidget()
            self._stack.addWidget(ph)
            self._widgets[i] = None

        self._setup_menu_bar()
        self._setup_toolbar()
        self._navigate(0)

    def _setup_menu_bar(self) -> None:
        """Menueleiste nach BudgetManager-Vorbild.

        Sie ersetzt Seiten- und Werkzeugleiste nicht, sondern ergaenzt sie:
        Wer FPM kennt, soll nach dem Update nicht umlernen muessen - wer aus
        dem BudgetManager kommt, findet Datei/Ansicht/Extras/Hilfe dort, wo
        er sie sucht.
        """
        from ui.menu_bar import build_menu_bar, sync_menu_state

        build_menu_bar(self)
        sync_menu_state(self)

    def show_onboarding_if_needed(self):
        """App-Tour anzeigen wenn DB leer und noch nicht abgeschlossen.

        Die alte OnboardingWizard-Datei bleibt im Projekt, aber der neue Start
        nutzt den besseren TourController mit Spotlight und Rundgang.
        """
        try:
            from ui.tour_controller import should_show_tour
            if not should_show_tour():
                return
            from PySide6.QtCore import QTimer
            QTimer.singleShot(250, self.start_tour)
        except Exception:
            # Fallback: alter Wizard, falls Tour-Dateien fehlen oder kaputt sind.
            try:
                from ui.onboarding_wizard import should_show_wizard
                if not should_show_wizard():
                    return
                self.start_onboarding_wizard()
            except Exception:
                return

    def start_onboarding_wizard(self) -> None:
        """Den vierstufigen Einrichtungsassistenten jederzeit starten."""
        from ui.onboarding_wizard import OnboardingWizard

        wizard = OnboardingWizard(self)
        wizard.navigate_to.connect(self._navigate)
        wizard.open_ink_dialog.connect(self._open_ink_add_dialog)
        wizard.open_pen_dialog.connect(self._open_pen_add_dialog)
        wizard.exec()

    def start_tour(self) -> None:
        """App-Tour starten (Hilfe, Einstellungen oder erster Start)."""
        from ui.tour_controller import TourController
        self._tour = TourController(self)
        self._tour.start()

    def _open_ink_add_dialog(self) -> bool:
        """Tinten-Hinzufügen-Dialog öffnen und Erfolg an die Tour melden."""
        self._navigate(2)
        widget = self._ensure_widget(2)
        add = getattr(widget, "_add", None)
        return bool(add()) if callable(add) else False

    def _open_pen_add_dialog(self) -> bool:
        """Füller-Hinzufügen-Dialog öffnen und Erfolg an die Tour melden."""
        self._navigate(1)
        widget = self._ensure_widget(1)
        add = getattr(widget, "_add", None)
        return bool(add()) if callable(add) else False

    def _open_wishlist_add_dialog(self):
        """Wishlist-Hinzufügen-Dialog direkt öffnen (für Tour-CTA)."""
        self._navigate(7)
        widget = self._ensure_widget(7)
        add = getattr(widget, "_add", None)
        if callable(add):
            add()

    def _setup_toolbar(self):
        toolbar = QToolBar(t('ui.main_window.quick_actions'), self)
        toolbar.setMovable(False)
        toolbar.setObjectName("mainToolbar")
        self.addToolBar(toolbar)

        toolbar.addAction(t('ui.main_window.add_pen'),  lambda: self._run_page_action(1, "_add"))
        toolbar.addAction(t('ui.main_window.add_ink'),   lambda: self._run_page_action(2, "_add"))
        toolbar.addAction(t('ui.main_window.fill'),          lambda: self._run_page_action(1, "_load_ink"))
        toolbar.addAction(t('ui.main_window.cleaned'),          lambda: self._run_page_action(1, "_mark_cleaned"))
        toolbar.addAction(t('ui.main_window.suggest_rotation'), lambda: self._run_page_action(5, "generate_suggestions"))
        toolbar.addSeparator()

        context_help = toolbar.addAction(t('ui.main_window.context_help'))
        context_help.setToolTip(t('ui.main_window.context_help_tooltip'))
        context_help.triggered.connect(self._open_context_help)
        toolbar.addSeparator()

        self.global_search = QLineEdit()
        self.global_search.setToolTip(t("ui.main_window.search_tooltip"))
        self.global_search.setPlaceholderText(t('ui.main_window.search_placeholder'))
        self.global_search.setClearButtonEnabled(True)
        self.global_search.textChanged.connect(self._global_search_changed)
        toolbar.addWidget(self.global_search)

    def _create_widget(self, index: int) -> QWidget:
        # Lokale Imports verhindern zirkuläre Startprobleme und machen Lazy Loading möglich.
        if index == 0:
            from ui.dashboard_widget import DashboardWidget
            return DashboardWidget()
        if index == 1:
            from ui.pen_widget import PenWidget
            return PenWidget()
        if index == 2:
            from ui.ink_widget import InkWidget
            return InkWidget()
        if index == 3:
            from ui.nib_widget import NibWidget
            return NibWidget()
        if index == 4:
            from ui.paper_widget import PaperWidget
            return PaperWidget()
        if index == 5:
            from ui.rotation_widget import RotationWidget
            return RotationWidget()
        if index == 6:
            from ui.expenses_widget import ExpensesWidget
            return ExpensesWidget()
        if index == 7:
            from ui.wishlist_widget import WishlistWidget
            return WishlistWidget()
        if index == 8:
            from ui.rules_widget import RulesWidget
            return RulesWidget()
        if index == 9:
            from ui.help_widget import HelpWidget
            return HelpWidget()
        if index == 10:
            from ui.settings_widget import SettingsWidget
            return SettingsWidget()
        if index == 11:
            from ui.statistics_widget import StatisticsWidget
            return StatisticsWidget()
        if index == 12:
            from ui.writing_samples_widget import WritingSamplesWidget
            return WritingSamplesWidget()
        if index == 13:
            from ui.enthusiast_lab_widget import EnthusiastLabWidget
            return EnthusiastLabWidget()
        return QWidget()

    def _ensure_widget(self, index: int) -> QWidget:
        widget = self._widgets.get(index)
        if widget is not None:
            return widget
        widget = self._create_widget(index)
        old = self._stack.widget(index)
        self._stack.removeWidget(old)
        old.deleteLater()
        self._stack.insertWidget(index, widget)
        self._widgets[index] = widget
        # Hilfe/Einstellungen können die App-Tour sofort starten.
        sig = getattr(widget, "tour_requested", None)
        if sig is not None:
            try:
                sig.connect(self.start_tour)
            except Exception:
                pass
        wizard_sig = getattr(widget, "wizard_requested", None)
        if wizard_sig is not None:
            try:
                wizard_sig.connect(self.start_onboarding_wizard)
            except Exception:
                pass
        # Dashboard-Kacheln dürfen auch Expertentabs direkt öffnen. Bei einem
        # bewussten Doppelklick wird dafür der Expertenmodus automatisch aktiviert.
        nav_sig = getattr(widget, "navigate_to", None)
        if nav_sig is not None:
            try:
                target = self._navigate_from_dashboard if index == 0 else self._navigate
                nav_sig.connect(target)
            except Exception:
                pass
        action_sig = getattr(widget, "action_requested", None)
        if action_sig is not None:
            try:
                action_sig.connect(self._run_page_action)
            except Exception:
                pass
        # Entf löscht den ausgewählten Eintrag — nur bei fokussierter Tabelle
        # (WidgetShortcut), damit Entf in Eingabefeldern normal funktioniert.
        table = getattr(widget, "table", None)
        if table is not None and hasattr(widget, "_delete"):
            from PySide6.QtCore import Qt as _Qt
            from PySide6.QtGui import QKeySequence, QShortcut
            sc = QShortcut(QKeySequence(QKeySequence.StandardKey.Delete), table)
            sc.setContext(_Qt.ShortcutContext.WidgetShortcut)
            sc.activated.connect(widget._delete)
        return widget

    def _navigate_from_dashboard(self, index: int) -> None:
        """Erfüllt die explizite Dashboard-Navigation auch für Expertentabs."""
        if not page_visible(index):
            self.sidebar.set_mode(EXPERT_MODE)
        self._navigate(index)

    def _run_page_action(self, index: int, method_name: str):
        self._navigate(index)
        widget = self._ensure_widget(index)
        method = getattr(widget, method_name, None)
        if callable(method):
            method()

    def _open_context_help(self) -> None:
        """Öffnet aus jedem Modul direkt das passende Wiki-Kapitel."""
        current = self._stack.currentIndex()
        topic_by_page = {
            0: "start",
            1: "data_entry",
            2: "data_entry",
            3: "data_entry",
            4: "data_entry",
            5: "rotation",
            6: "consumption",
            7: "start",
            8: "rules",
            9: "start",
            10: "start",
            11: "start",
            12: "data_entry",
            13: "service",
        }
        self._navigate(9)
        help_widget = self._ensure_widget(9)
        show_topic = getattr(help_widget, "show_topic", None)
        if callable(show_topic):
            show_topic(topic_by_page.get(current, "start"))

    def _global_search_changed(self, text: str):
        widget = self._widgets.get(self._stack.currentIndex())
        search = getattr(widget, "search_edit", None) if widget is not None else None
        if search is not None and search.text() != text:
            search.setText(text)

    def _navigation_mode_changed(self, mode: str) -> None:
        from ui.menu_bar import sync_menu_state

        sync_menu_state(self)
        current = self._stack.currentIndex()
        target = fallback_page(current, mode)
        if target != current:
            self._navigate(target)
        else:
            self.sidebar.set_current_page(current)

    def set_navigation_mode(self, mode: str) -> str:
        """Navigationsmodus setzen und Seitenleiste sofort synchronisieren."""
        normalized = self.sidebar.set_mode(mode)
        self._navigation_mode_changed(normalized)
        return normalized

    def _navigate(self, index: int):
        index = fallback_page(index)
        widget = self._ensure_widget(index)
        self._stack.setCurrentIndex(index)
        self.sidebar.set_current_page(index)
        search = getattr(widget, "search_edit", None)
        self.global_search.blockSignals(True)
        self.global_search.setText(search.text() if search is not None else "")
        self.global_search.blockSignals(False)
        self._refresh_current()

    def _refresh_current(self):
        widget = self._widgets.get(self._stack.currentIndex())
        if widget is not None and hasattr(widget, "refresh"):
            widget.refresh()
        # Static texts are set through explicit t("...") calls.  Do not walk
        # the whole widget tree on every refresh; that was the costly runtime
        # i18n path removed in v0.2.44.
