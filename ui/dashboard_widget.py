"""
Dashboard – Übersicht mit Statistiken, Safety-Timer-Warnungen und Aktivitätslog.

FIX v0.2.3:
- Toten Code _set_card() entfernt.
- Karten-Update über benannte Helfer-Methode statt fragiles Lambda.
- Sammlungswert-Berechnung dokumentiert: Tinten werden mit Kaufpreis gewertet,
  da kein Marktwert für Tinten vorhanden ist.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QScrollArea, QMenu, QApplication, QPushButton,
    QGridLayout, QSizePolicy, QFrame,
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor, QFont, QKeyEvent, QMouseEvent

from database.db import get_session
from i18n.translator import LocaleService, format_money, t
from logic.event_bus import AppEventBus
from logic.rule_engine import RuleEngine
from logic.collection_health_service import build_collection_health
from logic.budget_export_service import load_budgetmanager_savings_goals


# ---------------------------------------------------------------------------
# Statistik-Karte
# ---------------------------------------------------------------------------
class DashboardTile(QFrame):
    """Kompakte Dashboard-Kachel mit getrenntem Einfach- und Doppelklick.

    Ein einfacher Klick wird kurz verzögert, damit ein Doppelklick nicht zuerst
    die Tabelle öffnet und unmittelbar danach die Seite wechselt.
    """

    clicked = Signal(str)
    double_clicked = Signal(int)

    def __init__(self, key: str, title: str, page: int, accent: str, parent=None):
        super().__init__(parent)
        self.key = key
        self.page = page
        self.accent = accent
        self._selected = False
        self.setObjectName("dashboardTile")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setMinimumHeight(104)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(5)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("dashboardTileTitle")
        self.primary_label = QLabel("–")
        self.primary_label.setObjectName("dashboardTilePrimary")
        self.primary_label.setWordWrap(True)
        self.detail_label = QLabel("")
        self.detail_label.setObjectName("dashboardTileDetail")
        self.detail_label.setWordWrap(True)
        self.open_button = QPushButton(t("dashboard.tiles.open_tab"))
        self.open_button.setObjectName("dashboardTileOpenButton")
        self.open_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_button.setToolTip(t("dashboard.tiles.open_tab_tooltip"))
        self.open_button.clicked.connect(lambda: self.double_clicked.emit(self.page))

        for label in (self.title_label, self.primary_label, self.detail_label):
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        layout.addWidget(self.title_label)
        layout.addWidget(self.primary_label)
        layout.addWidget(self.detail_label)
        layout.addStretch(1)
        layout.addWidget(self.open_button, 0, Qt.AlignmentFlag.AlignRight)

        self._single_click_timer = QTimer(self)
        self._single_click_timer.setSingleShot(True)
        self._single_click_timer.timeout.connect(lambda: self.clicked.emit(self.key))
        self._apply_style()

    def set_summary(self, primary: str, detail: str = "") -> None:
        self.primary_label.setText(primary or "–")
        self.detail_label.setText(detail or "")

    def set_selected(self, selected: bool) -> None:
        selected = bool(selected)
        if self._selected == selected:
            return
        self._selected = selected
        self._apply_style()

    def _apply_style(self) -> None:
        border = self.accent if self._selected else "#d5dce6"
        background = "#eff6ff" if self._selected else "#ffffff"
        self.setStyleSheet(f"""
            QFrame#dashboardTile {{
                background: {background};
                border: 2px solid {border};
                border-radius: 9px;
            }}
            QFrame#dashboardTile:hover {{
                background: #f8fbff;
                border-color: {self.accent};
            }}
            QLabel#dashboardTileTitle {{
                color: {self.accent};
                border: none;
                font-size: 12px;
                font-weight: 800;
            }}
            QLabel#dashboardTilePrimary {{
                color: #1e2a38;
                border: none;
                font-size: 17px;
                font-weight: 800;
            }}
            QLabel#dashboardTileDetail {{
                color: #5f6f72;
                border: none;
                font-size: 12px;
            }}
            QPushButton#dashboardTileOpenButton {{
                color: {self.accent};
                background: transparent;
                border: 1px solid {self.accent};
                border-radius: 5px;
                padding: 3px 8px;
                min-height: 22px;
                font-size: 11px;
                font-weight: 700;
            }}
            QPushButton#dashboardTileOpenButton:hover {{
                color: white;
                background: {self.accent};
            }}
        """)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            interval = max(180, int(QApplication.doubleClickInterval()))
            self._single_click_timer.start(interval)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._single_click_timer.stop()
            self.double_clicked.emit(self.page)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self.double_clicked.emit(self.page)
            else:
                self.clicked.emit(self.key)
            event.accept()
            return
        super().keyPressEvent(event)


# ---------------------------------------------------------------------------
# Dashboard-Widget
# ---------------------------------------------------------------------------
class DashboardWidget(QWidget):
    # Wird von den Rechtsklick-Menüs der Tabellen emittiert, damit das
    # Hauptfenster zur passenden Seite springen kann (Muster wie tour_requested).
    navigate_to = Signal(int)
    action_requested = Signal(int, str)

    def __init__(self):
        super().__init__()
        self._setup_ui()
        # EventBus: Dashboard refresht sich wenn Füller, Tinten oder Ausgaben geändert werden.
        # Ausgaben können pen.purchase_price/service_cost synchronisieren.
        bus = AppEventBus.instance()
        bus.pens_changed.connect(self.refresh)
        bus.inks_changed.connect(self.refresh)
        bus.expenses_changed.connect(self.refresh)

    def _setup_ui(self):
        # Das Dashboard ist eine kompakte Kachelübersicht. Detailtabellen werden
        # erst nach einem Klick eingeblendet; dadurch bleibt die Laptopansicht
        # ruhig und kurz, ohne Informationen zu verstecken.
        host = QVBoxLayout(self)
        host.setContentsMargins(0, 0, 0, 0)
        host.setSpacing(0)

        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        host.addWidget(self._scroll)

        content = QWidget()
        content.setObjectName("dashboardScrollContent")
        content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._scroll.setWidget(content)

        outer = QVBoxLayout(content)
        outer.setContentsMargins(18, 16, 18, 18)
        outer.setSpacing(12)
        self._content_layout = outer

        title = QLabel(t('ui.dashboard_widget.dashboard_25b5cd12'))
        title.setObjectName("page_title")
        outer.addWidget(title)

        self._onboarding = QGroupBox(t("tour.quickstart.title"))
        self._onboarding.setStyleSheet(
            "QGroupBox { background:#eff6ff; border:2px solid #3b82f6; border-radius:8px; }"
        )
        ob_layout = QVBoxLayout(self._onboarding)
        ob_text = QLabel(t("tour.quickstart.body"))
        ob_text.setWordWrap(True)
        ob_text.setStyleSheet("border:none; color:#1e3a5f; font-size:13px;")
        ob_layout.addWidget(ob_text)
        self._onboarding.setVisible(False)
        outer.addWidget(self._onboarding)

        quick_group = QGroupBox(t("dashboard.quick_actions.title"))
        quick_layout = QVBoxLayout(quick_group)
        quick_hint = QLabel(t("dashboard.quick_actions.hint"))
        quick_hint.setWordWrap(True)
        quick_hint.setStyleSheet("border:none; color:#475569; font-size:13px;")
        quick_layout.addWidget(quick_hint)
        self._quick_buttons_layout = QGridLayout()
        self._quick_buttons_layout.setHorizontalSpacing(8)
        self._quick_buttons_layout.setVerticalSpacing(8)
        self._quick_buttons = []
        for label_key, page, method in (
            ("dashboard.quick_actions.add_pen", 1, "_add"),
            ("dashboard.quick_actions.add_ink", 2, "_add"),
            ("dashboard.quick_actions.fill_pen", 1, "_load_ink"),
            ("dashboard.quick_actions.clean_pen", 1, "_mark_cleaned"),
        ):
            btn = QPushButton(t(label_key))
            btn.setObjectName("dashboardPrimaryAction")
            btn.clicked.connect(lambda checked=False, p=page, m=method: self.action_requested.emit(p, m))
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self._quick_buttons.append(btn)
        quick_layout.addLayout(self._quick_buttons_layout)
        outer.addWidget(quick_group)

        tile_hint = QLabel(t("dashboard.tiles.interaction_hint"))
        tile_hint.setWordWrap(True)
        tile_hint.setStyleSheet("color:#64748b; border:none; padding:0 2px;")
        outer.addWidget(tile_hint)

        self._tiles_grid = QGridLayout()
        self._tiles_grid.setHorizontalSpacing(10)
        self._tiles_grid.setVerticalSpacing(10)
        self._tile_collection = DashboardTile(
            "collection", t("dashboard.tiles.collection.title"), 11, "#8e44ad", content
        )
        self._tile_rotation = DashboardTile(
            "rotation", t("dashboard.tiles.rotation.title"), 5, "#d35400", content
        )
        self._tile_service = DashboardTile(
            "service", t("dashboard.tiles.service.title"), 1, "#c0392b", content
        )
        self._tile_activity = DashboardTile(
            "activity", t("dashboard.tiles.activity.title"), 5, "#2471a3", content
        )
        self._tile_budget = DashboardTile(
            "budget", t("dashboard.tiles.budget.title"), 6, "#168f6a", content
        )
        self._tiles = (
            self._tile_collection,
            self._tile_rotation,
            self._tile_service,
            self._tile_activity,
            self._tile_budget,
        )
        self._tiles_by_key = {tile.key: tile for tile in self._tiles}
        for tile in self._tiles:
            tile.clicked.connect(self._toggle_detail)
            tile.double_clicked.connect(self.navigate_to.emit)
        self._tile_budget.setVisible(False)
        outer.addLayout(self._tiles_grid)

        self._detail_groups: dict[str, QGroupBox] = {}
        self._detail_tables: dict[str, QTableWidget] = {}
        self._expanded_detail: str | None = None

        self.bm_goals_group = QGroupBox(t("budget_goals.title"))
        bm_goals_layout = QVBoxLayout(self.bm_goals_group)
        bm_goals_hint = QLabel(t("budget_goals.hint"))
        bm_goals_hint.setWordWrap(True)
        bm_goals_hint.setStyleSheet("color:#5f6f72; border:none; padding:2px;")
        bm_goals_layout.addWidget(bm_goals_hint)
        self.bm_goals_table = QTableWidget()
        self._prepare_table(self.bm_goals_table)
        self.bm_goals_table.setColumnCount(5)
        self.bm_goals_table.setHorizontalHeaderLabels([
            t("budget_goals.headers.goal"),
            t("budget_goals.headers.progress"),
            t("budget_goals.headers.current_target"),
            t("budget_goals.headers.remaining"),
            t("budget_goals.headers.deadline_status"),
        ])
        self.bm_goals_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.bm_goals_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.bm_goals_table.setAlternatingRowColors(True)
        bm_goals_layout.addWidget(self.bm_goals_table)
        outer.addWidget(self.bm_goals_group)
        self._register_detail("budget", self.bm_goals_group, self.bm_goals_table, 6)

        self._timer_group = QGroupBox(
            t('ui.dashboard_widget.ink_safety_timer_tinten_mit_langer_standzeit_d2a1f605')
        )
        timer_layout = QVBoxLayout(self._timer_group)
        self.timer_table = QTableWidget()
        self._prepare_table(self.timer_table)
        self.timer_table.setColumnCount(5)
        self.timer_table.setHorizontalHeaderLabels([
            t('ui.dashboard_widget.fuller_f8544bb5'),
            t('ui.dashboard_widget.tinte_67575656'),
            t('ui.dashboard_widget.eingefullt_tage_84b9bdb1'),
            t('ui.dashboard_widget.max_tage_fd6d6777'),
            t('ui.dashboard_widget.status_b9296686'),
        ])
        self.timer_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.timer_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.timer_table.setAlternatingRowColors(True)
        self.timer_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.timer_table.customContextMenuRequested.connect(
            lambda pos: self._table_menu(self.timer_table, pos, pen_col=0, ink_col=1)
        )
        timer_layout.addWidget(self.timer_table)
        outer.addWidget(self._timer_group)
        self._register_detail("rotation", self._timer_group, self.timer_table, 5)

        self._lock_group = QGroupBox(t('ui.dashboard_widget.service_sperren_e9cbcd0b'))
        lock_layout = QVBoxLayout(self._lock_group)
        lock_hint = QLabel(t('ui.dashboard_widget.zeigt_fuller_im_service_manuelle_sperren_und_kri_affc2843'))
        lock_hint.setWordWrap(True)
        lock_hint.setStyleSheet("color:#5f6f72; border:none; padding:2px;")
        lock_layout.addWidget(lock_hint)
        self.service_table = QTableWidget()
        self._prepare_table(self.service_table)
        self.service_table.setColumnCount(5)
        self.service_table.setHorizontalHeaderLabels([
            t('ui.dashboard_widget.fuller_f8544bb5'),
            t('ui.dashboard_widget.status_b9296686'),
            t('ui.dashboard_widget.grund_f6662f1d'),
            t('ui.dashboard_widget.bis_tage_a2f3c21a'),
            t('ui.dashboard_widget.aktion_4256e9e9'),
        ])
        self.service_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.service_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.service_table.setAlternatingRowColors(True)
        self.service_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.service_table.customContextMenuRequested.connect(
            lambda pos: self._table_menu(self.service_table, pos, pen_col=0, ink_col=None)
        )
        lock_layout.addWidget(self.service_table)
        outer.addWidget(self._lock_group)
        self._register_detail("service", self._lock_group, self.service_table, 1)

        self._health_group = QGroupBox(t("collector_health.title"))
        health_layout = QVBoxLayout(self._health_group)
        health_hint = QLabel(t("collector_health.hint"))
        health_hint.setWordWrap(True)
        health_hint.setStyleSheet("color:#5f6f72; border:none; padding:2px;")
        health_layout.addWidget(health_hint)
        self.health_table = QTableWidget()
        self._prepare_table(self.health_table)
        self.health_table.setColumnCount(5)
        self.health_table.setHorizontalHeaderLabels([
            t("collector_health.headers.area"),
            t("collector_health.headers.severity"),
            t("collector_health.headers.item"),
            t("collector_health.headers.issue"),
            t("collector_health.headers.action"),
        ])
        self.health_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.health_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.health_table.setAlternatingRowColors(True)
        self.health_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.health_table.customContextMenuRequested.connect(
            lambda pos: self._table_menu(self.health_table, pos, pen_col=None, ink_col=None)
        )
        health_layout.addWidget(self.health_table)
        outer.addWidget(self._health_group)
        self._register_detail("collection", self._health_group, self.health_table, 11)

        self._activity_group = QGroupBox(t('ui.dashboard_widget.letzte_einfullungen_60912e9a'))
        act_layout = QVBoxLayout(self._activity_group)
        self.activity_table = QTableWidget()
        self._prepare_table(self.activity_table)
        self.activity_table.setColumnCount(4)
        self.activity_table.setHorizontalHeaderLabels([
            t('ui.dashboard_widget.fuller_f8544bb5'),
            t('ui.dashboard_widget.tinte_67575656'),
            t('ui.dashboard_widget.eingefullt_am_3cf01df9'),
            t('ui.dashboard_widget.gereinigt_am_a37d0d93'),
        ])
        self.activity_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.activity_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.activity_table.setAlternatingRowColors(True)
        self.activity_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.activity_table.customContextMenuRequested.connect(
            lambda pos: self._table_menu(self.activity_table, pos, pen_col=0, ink_col=1)
        )
        act_layout.addWidget(self.activity_table)
        outer.addWidget(self._activity_group)
        self._register_detail("activity", self._activity_group, self.activity_table, 5)

        self._all_clear = QLabel(t("dashboard.all_clear"))
        self._all_clear.setWordWrap(True)
        self._all_clear.setStyleSheet(
            "background:#ecfdf5; border:1px solid #10b981; border-radius:8px;"
            " color:#065f46; padding:12px; font-size:13px;"
        )
        self._all_clear.setVisible(False)
        outer.addWidget(self._all_clear)
        outer.addStretch()

        self._sync_detail_visibility()
        self._apply_responsive_layout(900)


    def _prepare_table(self, table: QTableWidget) -> None:
        """Bereitet eine Tabelle für die jeweils einzige geöffnete Detailfläche vor."""
        table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        table.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        table.setVerticalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        table.verticalHeader().setVisible(False)
        table.setWordWrap(False)
        table.setMinimumHeight(220)
        table.setMaximumHeight(420)

    def _register_detail(
        self,
        key: str,
        group: QGroupBox,
        table: QTableWidget,
        page: int,
    ) -> None:
        self._detail_groups[key] = group
        self._detail_tables[key] = table
        group.setVisible(False)
        table.cellDoubleClicked.connect(
            lambda _row, _column, target=page: self.navigate_to.emit(target)
        )

    def _toggle_detail(self, key: str) -> None:
        """Öffnet exklusiv die gewählte Tabelle; erneuter Klick klappt sie ein."""
        if key not in self._detail_groups:
            return
        tile = self._tiles_by_key.get(key)
        if tile is None or tile.isHidden():
            return
        self._expanded_detail = None if self._expanded_detail == key else key
        self._sync_detail_visibility()
        if self._expanded_detail:
            group = self._detail_groups[self._expanded_detail]
            table = self._detail_tables[self._expanded_detail]
            table.setFocus(Qt.FocusReason.OtherFocusReason)
            QTimer.singleShot(0, lambda target=group: self._scroll.ensureWidgetVisible(target, 0, 24))

    def _sync_detail_visibility(self) -> None:
        if self._expanded_detail:
            tile = self._tiles_by_key.get(self._expanded_detail)
            if tile is None or tile.isHidden():
                self._expanded_detail = None
        for key, group in self._detail_groups.items():
            selected = key == self._expanded_detail
            group.setVisible(selected)
            tile = self._tiles_by_key.get(key)
            if tile is not None:
                tile.set_selected(selected)

    @staticmethod
    def _clear_grid(layout: QGridLayout) -> None:
        while layout.count():
            layout.takeAt(0)

    def _apply_responsive_layout(self, width: int) -> None:
        """Ordnet Schnellaktionen und sichtbare Kacheln passend zur Breite neu an."""
        if width < 560:
            tile_columns, action_columns = 1, 1
        elif width < 1020:
            tile_columns, action_columns = 2, 2
        else:
            tile_columns, action_columns = 3, 4

        self._clear_grid(self._tiles_grid)
        visible_tiles = [tile for tile in self._tiles if not tile.isHidden()]
        for index, tile in enumerate(visible_tiles):
            self._tiles_grid.addWidget(tile, index // tile_columns, index % tile_columns)
        for column in range(tile_columns):
            self._tiles_grid.setColumnStretch(column, 1)

        self._clear_grid(self._quick_buttons_layout)
        for index, button in enumerate(self._quick_buttons):
            self._quick_buttons_layout.addWidget(
                button, index // action_columns, index % action_columns
            )
        for column in range(action_columns):
            self._quick_buttons_layout.setColumnStretch(column, 1)

    def _sync_responsive_layout(self) -> None:
        viewport_width = self._scroll.viewport().width() if hasattr(self, "_scroll") else self.width()
        self._apply_responsive_layout(max(320, viewport_width - 36))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._sync_responsive_layout()
        # QScrollArea berechnet seine Viewport-Breite erst nach dem ersten
        # Layoutdurchlauf zuverlässig. Der verzögerte zweite Lauf verhindert,
        # dass das Dashboard nach dem Öffnen fälschlich im Einspaltenmodus bleibt.
        QTimer.singleShot(0, self._sync_responsive_layout)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._sync_responsive_layout)

    # ------------------------------------------------------------------ #
    # Rechtsklick-Menü für die Dashboard-Tabellen                          #
    # ------------------------------------------------------------------ #
    def _table_menu(self, table, pos, *, pen_col=None, ink_col=None):
        """Gemeinsames Kontextmenü: springen, Details kopieren, aktualisieren."""
        item = table.itemAt(pos)
        row = item.row() if item is not None else -1
        menu = QMenu(self)

        act_pen = menu.addAction(t("dashboard.context.jump_to_pen")) if pen_col is not None else None
        act_ink = menu.addAction(t("dashboard.context.jump_to_ink")) if ink_col is not None else None
        if act_pen or act_ink:
            menu.addSeparator()
        act_copy = menu.addAction(t("dashboard.context.copy_details")) if row >= 0 else None
        act_refresh = menu.addAction(t("dashboard.context.refresh"))

        chosen = menu.exec(table.viewport().mapToGlobal(pos))
        if chosen is None:
            return
        if chosen is act_pen:
            self.navigate_to.emit(1)      # Füller-Seite
        elif chosen is act_ink:
            self.navigate_to.emit(2)      # Tinten-Seite
        elif chosen is act_copy and row >= 0:
            cells = []
            for col in range(table.columnCount()):
                cell = table.item(row, col)
                if cell and cell.text():
                    cells.append(cell.text())
            clip = QApplication.clipboard()
            if clip is not None:
                clip.setText(" · ".join(cells))
        elif chosen is act_refresh:
            self.refresh()

    def refresh(self):
        """Dashboard neu aufbauen.

        v0.3.01 (Enterprise-Audit P1): Die frühere 309-Zeilen-Methode ist in
        den Qt-freien ``logic.dashboard_service`` (Datenbeschaffung,
        Klassifikation, Schwellwerte, Texte) und kleine Renderer unten
        zerlegt. Dieses Widget enthält keine direkten ``session.query``-
        Aufrufe mehr; der Service arbeitet über die Repository-Schicht.
        """
        from logic.dashboard_service import collect_dashboard_data
        session = get_session()
        try:
            lc = LocaleService.instance()
            rule_engine = RuleEngine()
            data = collect_dashboard_data(
                session,
                max_days_for=lambda pen, ink: rule_engine.max_days_for(pen, ink, session),
                convert=lc.convert_to_default,
                default_currency=lc.currency,
                budget_goals_loader=load_budgetmanager_savings_goals,
                health_builder=build_collection_health,
            )
        finally:
            session.close()

        self._onboarding.setVisible(data.show_onboarding)
        self._render_budget(data)
        self._render_timer(data)
        self._render_service(data)
        self._render_health(data)
        self._render_activity(data)

        self._sync_detail_visibility()
        viewport_width = self._scroll.viewport().width() if self._scroll else self.width()
        self._apply_responsive_layout(max(320, viewport_width - 36))
        self._all_clear.setVisible(data.all_clear)

    # ── Renderer (nur Qt-Darstellung, keine Datenlogik) ──────────────────

    def _render_budget(self, data) -> None:
        goals = data.budget_goals
        self._tile_budget.setVisible(bool(goals))
        if not goals and self._expanded_detail == "budget":
            self._expanded_detail = None
        self.bm_goals_table.setRowCount(len(goals))
        for row, goal in enumerate(goals):
            goal_title = goal.label
            if goal.goal_name and goal.goal_name != goal.label:
                goal_title = f"{goal.label} — {goal.goal_name}"
            values = [
                goal_title,
                f"{goal.progress_percent:.1f}%",
                f"{format_money(goal.current_amount, goal.currency)} / {format_money(goal.target_amount, goal.currency)}",
                format_money(goal.remaining_amount, goal.currency),
                f"{goal.deadline or '—'} · {goal.status}",
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 1 and goal.progress_percent >= 100:
                    item.setForeground(QColor("#27ae60"))
                    item.setFont(QFont("", -1, QFont.Weight.Bold))
                elif col == 3 and goal.remaining_amount > 0:
                    item.setForeground(QColor("#d35400"))
                self.bm_goals_table.setItem(row, col, item)
        if goals:
            self._tile_budget.set_summary(
                t("dashboard.tiles.budget.primary", count=len(goals), complete=data.budget_completed),
                t("dashboard.tiles.budget.detail", remaining=data.budget_remaining_str),
            )

    def _render_timer(self, data) -> None:
        self._timer_group.setTitle(
            t('dashboard.timer_title_counts', overdue=data.timer_overdue, soon=data.timer_due_soon)
        )
        self._tile_rotation.set_summary(
            t("dashboard.tiles.rotation.primary", active=data.active_loads_count, overdue=data.timer_overdue),
            t("dashboard.tiles.rotation.detail", soon=data.timer_due_soon),
        )
        rows = data.timer_rows
        self.timer_table.setRowCount(len(rows))
        for row, entry in enumerate(rows):
            self.timer_table.setItem(row, 0, QTableWidgetItem(entry["pen"]))
            self.timer_table.setItem(row, 1, QTableWidgetItem(entry["ink"]))
            days_item = QTableWidgetItem(str(entry["days"]))
            if entry["overdue"]:
                days_item.setForeground(QColor("#e74c3c"))
                days_item.setFont(QFont("", -1, QFont.Weight.Bold))
            self.timer_table.setItem(row, 2, days_item)
            self.timer_table.setItem(row, 3, QTableWidgetItem(str(entry["max"])))
            status = t("common.overdue_bang") if entry["overdue"] else "🟢 " + t("common.ok")
            status_item = QTableWidgetItem(status)
            if entry["overdue"]:
                status_item.setForeground(QColor("#e74c3c"))
            self.timer_table.setItem(row, 4, status_item)

    def _render_service(self, data) -> None:
        rows = data.service_rows
        self._lock_group.setTitle(t('dashboard.lock_title_counts', count=len(rows)))
        self._tile_service.set_summary(
            t("dashboard.tiles.service.primary", count=len(rows)),
            t("dashboard.tiles.service.detail", critical=data.service_critical, blocked=data.service_blocked),
        )
        self.service_table.setRowCount(len(rows))
        for row, entry in enumerate(rows):
            values = [entry["pen"], entry["status"], entry["reason"], entry["until"], entry["action"]]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value or "—")
                severity = entry.get("severity")
                if severity in ("critical", "blocked"):
                    item.setForeground(QColor("#e74c3c" if severity == "critical" else "#8e44ad"))
                    if col in (0, 1):
                        item.setFont(QFont("", -1, QFont.Weight.Bold))
                elif severity == "warning":
                    item.setForeground(QColor("#d35400"))
                self.service_table.setItem(row, col, item)

    def _render_health(self, data) -> None:
        rows = data.health_rows
        self.health_table.setRowCount(len(rows))
        severity_icon = {"critical": "🔴", "warning": "🟠", "info": "🔵"}
        severity_color = {"critical": "#e74c3c", "warning": "#d35400", "info": "#2563eb"}
        self._tile_collection.set_summary(
            t("dashboard.tiles.collection.primary", pens=data.pens_total, inks=data.inks_total),
            t(
                "dashboard.tiles.collection.detail",
                value=data.value_str,
                issues=len(rows),
                archived=data.archived_total,
            ),
        )
        collection_tip = t(
            "dashboard.tiles.collection.tooltip",
            critical=data.health_critical,
            warning=data.health_warning,
            missing=data.missing_currency,
        )
        if data.has_mixed_currencies:
            lc = LocaleService.instance()
            collection_tip += "\n" + t(
                'ui.dashboard_widget.value_mixed_tooltip',
                currency=lc.currency,
                currencies=', '.join(sorted(data.currencies_used)),
                extra=t('ui.dashboard_widget.value_missing_currency_hint', count=data.missing_currency) if data.missing_currency else "",
            )
        self._tile_collection.setToolTip(collection_tip)
        for row, entry in enumerate(rows):
            area = t(f"collector_health.area.{entry.area}")
            severity = f"{severity_icon.get(entry.severity, '•')} {t(f'collector_health.severity.{entry.severity}')}"
            issue = t(f"collector_health.issue.{entry.code}", detail=entry.detail)
            action = t(f"collector_health.action.{entry.action}") if entry.action else "—"
            values = [area, severity, entry.entity, issue, action]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value or "—")
                if col == 1:
                    item.setForeground(QColor(severity_color.get(entry.severity, "#2c3e50")))
                    if entry.severity in ("critical", "warning"):
                        item.setFont(QFont("", -1, QFont.Weight.Bold))
                self.health_table.setItem(row, col, item)

    def _render_activity(self, data) -> None:
        rows = data.activity_rows
        self.activity_table.setRowCount(len(rows))
        for row, entry in enumerate(rows):
            self.activity_table.setItem(row, 0, QTableWidgetItem(entry["pen"]))
            self.activity_table.setItem(row, 1, QTableWidgetItem(entry["ink"]))
            self.activity_table.setItem(row, 2, QTableWidgetItem(entry["loaded"]))
            self.activity_table.setItem(row, 3, QTableWidgetItem(entry["cleaned"]))
        self._tile_activity.set_summary(
            t("dashboard.tiles.activity.primary", count=len(rows)),
            t("dashboard.tiles.activity.detail", last=data.last_activity),
        )
