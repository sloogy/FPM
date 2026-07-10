"""
Dashboard – Übersicht mit Statistiken, Safety-Timer-Warnungen und Aktivitätslog.

FIX v0.2.3:
- Toten Code _set_card() entfernt.
- Karten-Update über benannte Helfer-Methode statt fragiles Lambda.
- Sammlungswert-Berechnung dokumentiert: Tinten werden mit Kaufpreis gewertet,
  da kein Marktwert für Tinten vorhanden ist.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QScrollArea, QMenu, QApplication, QPushButton,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont

from database.db import get_session
from database.models import Pen, Ink, InkLoad, Expense, Paper
from i18n.translator import LocaleService, format_money, format_date, t
from logic.event_bus import AppEventBus
from logic.rule_engine import RuleEngine
from logic.collection_health_service import build_collection_health
from logic.budget_export_service import load_budgetmanager_savings_goals
from PySide6.QtWidgets import QFrame


# ---------------------------------------------------------------------------
# Statistik-Karte
# ---------------------------------------------------------------------------
def _card(value: str, label: str, color: str = "#2c3e50") -> QWidget:
    w = QWidget()
    w.setStyleSheet("background:white; border-radius:8px; border:1px solid #d5dce6;")
    lay = QVBoxLayout(w)
    lay.setContentsMargins(18, 16, 18, 16)

    val_lbl = QLabel(value)
    val_lbl.setObjectName("card_value")
    val_lbl.setStyleSheet(f"font-size:30px; font-weight:bold; color:{color}; border:none;")
    val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

    txt_lbl = QLabel(label)
    txt_lbl.setStyleSheet("font-size:12px; color:#7f8c8d; letter-spacing:1px; border:none;")
    txt_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

    lay.addWidget(val_lbl)
    lay.addWidget(txt_lbl)
    return w


def _set_card_value(card_widget: QWidget, text: str) -> None:
    """Setzt den Hauptwert-Label einer Statistik-Karte."""
    lbl = card_widget.findChild(QLabel, "card_value")
    if lbl:
        lbl.setText(text)


BLOCKING_STATUSES = {"problem", "service", "blocked", "dry_risk"}
def _status_label(key: str | None) -> str:
    return t(f"dashboard.status_labels.{key}") if key else ""

def _pen_name(pen: Pen) -> str:
    return f"{pen.brand} {pen.model}".strip()


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
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(20)

        # Titel
        title = QLabel(t('ui.dashboard_widget.dashboard_25b5cd12'))
        title.setObjectName("page_title")
        outer.addWidget(title)

        # ── Onboarding (erscheint nur bei leerer DB) ────────────────────
        self._onboarding = QGroupBox(t("tour.quickstart.title"))
        self._onboarding.setStyleSheet(
            "QGroupBox { background:#eff6ff; border:2px solid #3b82f6; border-radius:8px; }"
        )
        ob_layout = QVBoxLayout(self._onboarding)
        ob_text = QLabel(t("tour.quickstart.body"))
        ob_text.setWordWrap(True)
        ob_text.setStyleSheet("border:none; color:#1e3a5f; font-size:13px;")
        ob_layout.addWidget(ob_text)
        self._onboarding.setVisible(False)  # initial ausgeblendet
        outer.addWidget(self._onboarding)

        # ── DAU-Schnellstart: genau die vier häufigsten Alltagsaktionen ──
        quick_group = QGroupBox(t("dashboard.quick_actions.title"))
        quick_layout = QVBoxLayout(quick_group)
        quick_hint = QLabel(t("dashboard.quick_actions.hint"))
        quick_hint.setWordWrap(True)
        quick_hint.setStyleSheet("border:none; color:#475569; font-size:13px;")
        quick_layout.addWidget(quick_hint)
        quick_buttons = QHBoxLayout()
        for label_key, page, method in (
            ("dashboard.quick_actions.add_pen", 1, "_add"),
            ("dashboard.quick_actions.add_ink", 2, "_add"),
            ("dashboard.quick_actions.fill_pen", 1, "_load_ink"),
            ("dashboard.quick_actions.clean_pen", 1, "_mark_cleaned"),
        ):
            btn = QPushButton(t(label_key))
            btn.setObjectName("dashboardPrimaryAction")
            btn.clicked.connect(lambda checked=False, p=page, m=method: self.action_requested.emit(p, m))
            quick_buttons.addWidget(btn)
        quick_buttons.addStretch(1)
        quick_layout.addLayout(quick_buttons)
        outer.addWidget(quick_group)

        # ── Stat-Karten ──────────────────────────────────────────────
        # v0.2.79: Entlastet – nur noch die vier Alltagswerte als grosse
        # Karten. Bestand/Service/Archiv wandern in eine kompakte Textzeile
        # darunter (Details weiterhin per Tooltip).
        cards_row = QHBoxLayout()
        cards_row.setSpacing(14)

        self._card_active = _card("–", t("dashboard.active_pens"),     "#27ae60")
        self._card_inks   = _card("–", t("dashboard.total_inks"),        "#3498db")
        self._card_warn   = _card("–", t("dashboard.ink_timer"),  "#e74c3c")
        self._card_value  = _card("–", t("dashboard.collection_value"), "#9b59b6")

        for c in (self._card_active, self._card_inks, self._card_warn, self._card_value):
            cards_row.addWidget(c)
        outer.addLayout(cards_row)

        self._inventory_line = QLabel("")
        self._inventory_line.setWordWrap(True)
        self._inventory_line.setStyleSheet(
            "color:#64748b; font-size:12px; border:none; padding:0 4px;"
        )
        outer.addWidget(self._inventory_line)

        # ── BudgetManager-Sparziele ─────────────────────────────────
        self.bm_goals_group = QGroupBox(t("budget_goals.title"))
        bm_goals_layout = QVBoxLayout(self.bm_goals_group)
        bm_goals_hint = QLabel(t("budget_goals.hint"))
        bm_goals_hint.setWordWrap(True)
        bm_goals_hint.setStyleSheet("color:#7f8c8d; border:none; padding:2px;")
        bm_goals_layout.addWidget(bm_goals_hint)

        self.bm_goals_table = QTableWidget()
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
        self.bm_goals_table.setMaximumHeight(170)
        bm_goals_layout.addWidget(self.bm_goals_table)
        self.bm_goals_group.setVisible(False)
        outer.addWidget(self.bm_goals_group)

        # ── Safety-Timer ────────────────────────────────────────────
        # ── Ink Safety Timer ─────────────────────────────────────────
        timer_group = QGroupBox(t('ui.dashboard_widget.ink_safety_timer_tinten_mit_langer_standzeit_d2a1f605'))
        self._timer_group = timer_group
        timer_layout = QVBoxLayout(timer_group)

        self.timer_table = QTableWidget()
        self.timer_table.setColumnCount(5)
        self.timer_table.setHorizontalHeaderLabels(
            [t('ui.dashboard_widget.fuller_f8544bb5'), t('ui.dashboard_widget.tinte_67575656'), t('ui.dashboard_widget.eingefullt_tage_84b9bdb1'), t('ui.dashboard_widget.max_tage_fd6d6777'), t('ui.dashboard_widget.status_b9296686')]
        )
        self.timer_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.timer_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.timer_table.setAlternatingRowColors(True)
        self.timer_table.setMaximumHeight(150)
        self.timer_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.timer_table.customContextMenuRequested.connect(
            lambda pos: self._table_menu(self.timer_table, pos, pen_col=0, ink_col=1)
        )
        timer_layout.addWidget(self.timer_table)
        outer.addWidget(timer_group)

        # ── Service & Sperren ───────────────────────────────────────
        lock_group = QGroupBox(t('ui.dashboard_widget.service_sperren_e9cbcd0b'))
        self._lock_group = lock_group
        lock_layout = QVBoxLayout(lock_group)
        lock_hint = QLabel(t('ui.dashboard_widget.zeigt_fuller_im_service_manuelle_sperren_und_kri_affc2843'))
        lock_hint.setWordWrap(True)
        lock_hint.setStyleSheet("color:#7f8c8d; border:none; padding:2px;")
        lock_layout.addWidget(lock_hint)

        self.service_table = QTableWidget()
        self.service_table.setColumnCount(5)
        self.service_table.setHorizontalHeaderLabels([t('ui.dashboard_widget.fuller_f8544bb5'), t('ui.dashboard_widget.status_b9296686'), t('ui.dashboard_widget.grund_f6662f1d'), t('ui.dashboard_widget.bis_tage_a2f3c21a'), t('ui.dashboard_widget.aktion_4256e9e9')])
        self.service_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.service_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.service_table.setAlternatingRowColors(True)
        self.service_table.setMaximumHeight(150)
        self.service_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.service_table.customContextMenuRequested.connect(
            lambda pos: self._table_menu(self.service_table, pos, pen_col=0, ink_col=None)
        )
        lock_layout.addWidget(self.service_table)
        outer.addWidget(lock_group)

        # ── Sammlungs-Advisor ─────────────────────────────────────
        health_group = QGroupBox(t("collector_health.title"))
        self._health_group = health_group
        health_layout = QVBoxLayout(health_group)
        health_hint = QLabel(t("collector_health.hint"))
        health_hint.setWordWrap(True)
        health_hint.setStyleSheet("color:#7f8c8d; border:none; padding:2px;")
        health_layout.addWidget(health_hint)

        self.health_table = QTableWidget()
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
        self.health_table.setMaximumHeight(165)
        self.health_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.health_table.customContextMenuRequested.connect(
            lambda pos: self._table_menu(self.health_table, pos, pen_col=None, ink_col=None)
        )
        health_layout.addWidget(self.health_table)
        outer.addWidget(health_group)

        # ── Letzte Aktivität ─────────────────────────────────────────
        activity_group = QGroupBox(t('ui.dashboard_widget.letzte_einfullungen_60912e9a'))
        self._activity_group = activity_group
        act_layout = QVBoxLayout(activity_group)

        self.activity_table = QTableWidget()
        self.activity_table.setColumnCount(4)
        self.activity_table.setHorizontalHeaderLabels(
            [t('ui.dashboard_widget.fuller_f8544bb5'), t('ui.dashboard_widget.tinte_67575656'), t('ui.dashboard_widget.eingefullt_am_3cf01df9'), t('ui.dashboard_widget.gereinigt_am_a37d0d93')]
        )
        self.activity_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.activity_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.activity_table.setAlternatingRowColors(True)
        self.activity_table.setMaximumHeight(150)
        self.activity_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.activity_table.customContextMenuRequested.connect(
            lambda pos: self._table_menu(self.activity_table, pos, pen_col=0, ink_col=1)
        )
        act_layout.addWidget(self.activity_table)
        outer.addWidget(activity_group)

        # ── „Alles im grünen Bereich"-Hinweis (nur wenn nichts ansteht) ──
        self._all_clear = QLabel(t("dashboard.all_clear"))
        self._all_clear.setWordWrap(True)
        self._all_clear.setStyleSheet(
            "background:#ecfdf5; border:1px solid #10b981; border-radius:8px;"
            " color:#065f46; padding:12px; font-size:13px;"
        )
        self._all_clear.setVisible(False)
        outer.addWidget(self._all_clear)

        outer.addStretch()

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
        session = get_session()
        try:
            pens_all = session.query(Pen).all()
            pens  = session.query(Pen).filter_by(is_active=True).all()
            archived_pens = [p for p in pens_all if not getattr(p, "is_active", True)]
            archived_inks_count = session.query(Ink).filter_by(is_archived=True).count()
            inks  = session.query(Ink).filter_by(is_archived=False).all()
            papers = session.query(Paper).all()
            expenses = session.query(Expense).all()
            loads = (
                session.query(InkLoad)
                .order_by(InkLoad.loaded_date.desc())
                .limit(8)
                .all()
            )

            total_pens   = len(pens)
            active_loads = [
                p.current_ink_load for p in pens
                if p.current_ink_load
                and getattr(p, "availability_status", "available") == "available"
                and not getattr(p, "rotation_blocked", False)
            ]

            # Sammlungswert: Währungsumrechnung via LocaleService
            lc = LocaleService.instance()
            currencies_used = set()
            total_value = 0.0
            missing_currency = 0
            for p in pens:
                if p.current_market_value:
                    raw = p.current_market_value or 0
                    pen_cur = getattr(p, "market_currency", None) or getattr(p, "purchase_currency", None)
                else:
                    raw = p.purchase_price or 0
                    pen_cur = getattr(p, "purchase_currency", None)
                if raw and not pen_cur:
                    missing_currency += 1
                    pen_cur = lc.currency
                pen_cur = pen_cur or lc.currency
                currencies_used.add(pen_cur)
                total_value += lc.convert_to_default(raw, pen_cur)
            for i in inks:
                raw = i.purchase_price or 0
                cur = getattr(i, "purchase_currency", None) or lc.currency
                if raw and not getattr(i, "purchase_currency", None):
                    missing_currency += 1
                currencies_used.add(cur)
                total_value += lc.convert_to_default(raw, cur)

            has_mixed = len(currencies_used) > 1
            value_str = format_money(total_value)
            if has_mixed:
                value_str += " ~"   # Tilde = umgerechnet/angenähert

            # Karten aktualisieren
            # Onboarding-Panel anzeigen wenn weder Füller noch Tinten vorhanden
            self._onboarding.setVisible(total_pens == 0 and len(inks) == 0)
            _set_card_value(self._card_active,  str(len(active_loads)))
            self._card_active.setToolTip(t('ui.dashboard_widget.pen_archive_tooltip', active=total_pens, archived=len(archived_pens)))
            _set_card_value(self._card_inks,    str(len(inks)))
            _set_card_value(self._card_value,   value_str)
            if has_mixed or missing_currency:
                extra = t('ui.dashboard_widget.value_missing_currency_hint', count=missing_currency) if missing_currency else ""
                self._card_value.setToolTip(
                    t('ui.dashboard_widget.value_mixed_tooltip', currency=lc.currency, currencies=', '.join(sorted(currencies_used)), extra=extra)
                )
            else:
                self._card_value.setToolTip("")

            # ── BudgetManager-Sparziele anzeigen ───────────────────
            try:
                bm_goals = load_budgetmanager_savings_goals()
            except Exception:
                bm_goals = []
            self.bm_goals_group.setVisible(bool(bm_goals))
            self.bm_goals_table.setRowCount(len(bm_goals))
            for row, goal in enumerate(bm_goals):
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

            # ── Service/Sperren sammeln ─────────────────────────────
            service_rows = []
            for pen in pens:
                status = getattr(pen, "availability_status", "available") or "available"
                if getattr(pen, "rotation_blocked", False) or status in BLOCKING_STATUSES:
                    until = getattr(pen, "blocked_until", None)
                    notes = getattr(pen, "service_notes", None) or t('ui.dashboard_widget.rotation_blocked')
                    action = t('ui.dashboard_widget.service_unlock_action') if status == "service" else t('ui.dashboard_widget.check_unlock_action')
                    service_rows.append({
                        "pen": _pen_name(pen),
                        "status": _status_label(status) or t('ui.dashboard_widget.blocked_status'),
                        "reason": notes,
                        "until": format_date(until) if until else t('ui.dashboard_widget.open_until'),
                        "action": action,
                        "severity": "blocked",
                    })

            # ── Safety-Timer Tabelle ─────────────────────────────────
            timer_rows = []
            warnings = 0
            for pen in pens:
                load = pen.current_ink_load
                if not load:
                    continue
                ink = session.get(Ink, load.ink_id)
                if not ink:
                    continue
                # Safety Timer nur zentral über RuleEngine berechnen, damit Dashboard
                # und Rotation dieselben Max-Tage/Warnungen anzeigen.
                max_days = RuleEngine().max_days_for(pen, ink, session)
                days    = load.days_loaded
                overdue = days > max_days
                if overdue:
                    warnings += 1
                timer_rows.append({
                    "pen":     f"{pen.brand} {pen.model}",
                    "ink":     f"{ink.brand} {ink.name}",
                    "days":    days,
                    "max":     max_days,
                    "overdue": overdue,
                })
                if overdue:
                    level = "critical" if days >= max_days + 7 else "warning"
                    service_rows.append({
                        "pen": _pen_name(pen),
                        "status": t('ui.dashboard_widget.dry_risk_status'),
                        "reason": t('ui.dashboard_widget.days_in_pen_reason', ink=f"{ink.brand} {ink.name}", days=days, max_days=max_days),
                        "until": t('ui.dashboard_widget.days_value', days=days),
                        "action": t('ui.dashboard_widget.clean_or_change_action'),
                        "severity": level,
                    })

            _set_card_value(self._card_warn, str(warnings))
            self._card_warn.setToolTip(t('ui.dashboard_widget.uberfallige_safety_timer_regelverstoe_erscheinen_40cc9f1a'))
            # v0.2.79: Bestand/Service/Archiv als kompakte Zeile statt Karten.
            self._inventory_line.setText(t(
                'dashboard.inventory_line',
                pens=total_pens,
                archived_pens=len(archived_pens),
                archived_inks=archived_inks_count,
                service=len(service_rows),
            ))
            self._inventory_line.setToolTip(
                t('ui.dashboard_widget.archived_tooltip', pens=len(archived_pens), inks=archived_inks_count)
                + "\n" + t('ui.dashboard_widget.service_tooltip', count=len(service_rows), warnings=warnings)
            )

            timer_rows.sort(key=lambda r: r["overdue"], reverse=True)
            # v0.2.79: Das Dashboard ist eine Alarmzentrale, keine Inventarliste.
            # Es zeigt nur überfällige und bald fällige Ladungen (≥ 80 % der
            # Maximaltage). Alles Grüne steht weiterhin auf der Rotationsseite.
            visible_timer_rows = [
                r for r in timer_rows
                if r["overdue"] or (r["max"] > 0 and r["days"] >= 0.8 * r["max"])
            ]
            due_soon = sum(1 for r in visible_timer_rows if not r["overdue"])
            self._timer_group.setTitle(
                t('dashboard.timer_title_counts', overdue=warnings, soon=due_soon)
            )
            self.timer_table.setRowCount(len(visible_timer_rows))
            for row, data in enumerate(visible_timer_rows):
                self.timer_table.setItem(row, 0, QTableWidgetItem(data["pen"]))
                self.timer_table.setItem(row, 1, QTableWidgetItem(data["ink"]))

                days_item = QTableWidgetItem(str(data["days"]))
                if data["overdue"]:
                    days_item.setForeground(QColor("#e74c3c"))
                    days_item.setFont(QFont("", -1, QFont.Weight.Bold))
                self.timer_table.setItem(row, 2, days_item)
                self.timer_table.setItem(row, 3, QTableWidgetItem(str(data["max"])))

                status      = t("common.overdue_bang") if data["overdue"] else "🟢 " + t("common.ok")
                status_item = QTableWidgetItem(status)
                if data["overdue"]:
                    status_item.setForeground(QColor("#e74c3c"))
                self.timer_table.setItem(row, 4, status_item)

            # ── Service/Sperren-Tabelle ─────────────────────────────
            self._lock_group.setTitle(t('dashboard.lock_title_counts', count=len(service_rows)))
            service_rows.sort(key=lambda r: {"critical": 0, "blocked": 1, "warning": 2}.get(r.get("severity"), 3))
            self.service_table.setRowCount(len(service_rows))
            for row, data in enumerate(service_rows):
                values = [data["pen"], data["status"], data["reason"], data["until"], data["action"]]
                for col, value in enumerate(values):
                    item = QTableWidgetItem(value or "—")
                    if data.get("severity") in ("critical", "blocked"):
                        item.setForeground(QColor("#e74c3c" if data.get("severity") == "critical" else "#8e44ad"))
                        if col in (0, 1):
                            item.setFont(QFont("", -1, QFont.Weight.Bold))
                    elif data.get("severity") == "warning":
                        item.setForeground(QColor("#d35400"))
                    self.service_table.setItem(row, col, item)


            # ── Sammlungs-Advisor ───────────────────────────────────
            def _max_days_for_health(pen, ink):
                try:
                    return RuleEngine().max_days_for(pen, ink, session)
                except Exception:
                    return int(getattr(ink, "max_days_in_pen", None) or 28)

            health_rows = build_collection_health(
                pens=pens,
                inks=inks,
                papers=papers,
                expenses=expenses,
                max_days_for_load=_max_days_for_health,
                limit=6,
            )
            self.health_table.setRowCount(len(health_rows))
            severity_icon = {
                "critical": "🔴",
                "warning": "🟠",
                "info": "🔵",
            }
            severity_color = {
                "critical": "#e74c3c",
                "warning": "#d35400",
                "info": "#2563eb",
            }
            for row, data in enumerate(health_rows):
                area = t(f"collector_health.area.{data.area}")
                severity = f"{severity_icon.get(data.severity, '•')} {t(f'collector_health.severity.{data.severity}')}"
                issue = t(f"collector_health.issue.{data.code}", detail=data.detail)
                action = t(f"collector_health.action.{data.action}") if data.action else "—"
                values = [area, severity, data.entity, issue, action]
                for col, value in enumerate(values):
                    item = QTableWidgetItem(value or "—")
                    if col == 1:
                        item.setForeground(QColor(severity_color.get(data.severity, "#2c3e50")))
                        if data.severity in ("critical", "warning"):
                            item.setFont(QFont("", -1, QFont.Weight.Bold))
                    self.health_table.setItem(row, col, item)

            # ── Aktivitäts-Tabelle ───────────────────────────────────
            self.activity_table.setRowCount(len(loads))
            for row, load in enumerate(loads):
                pen = session.get(Pen, load.pen_id)
                ink = session.get(Ink, load.ink_id)
                pen_txt = f"{pen.brand} {pen.model}" if pen else "?"
                ink_txt = f"{ink.brand} {ink.name}"  if ink else "?"
                loaded  = format_date(load.loaded_date)
                cleaned = format_date(load.cleaned_date) if load.cleaned_date else "—"

                self.activity_table.setItem(row, 0, QTableWidgetItem(pen_txt))
                self.activity_table.setItem(row, 1, QTableWidgetItem(ink_txt))
                self.activity_table.setItem(row, 2, QTableWidgetItem(loaded))
                self.activity_table.setItem(row, 3, QTableWidgetItem(cleaned))

            # ── Übersichtlichkeit: leere Abschnitte ausblenden ──────────
            # Ein aufgeräumtes Dashboard zeigt nur, was gerade relevant ist.
            self._timer_group.setVisible(bool(visible_timer_rows))
            self._lock_group.setVisible(bool(service_rows))
            self._health_group.setVisible(bool(health_rows))
            self._activity_group.setVisible(bool(loads))

            # „Alles im grünen Bereich" nur, wenn es überhaupt Inventar gibt und
            # keine Warnungen, kein Service und keine Advisor-Hinweise anstehen.
            has_inventory = bool(pens or inks)
            nothing_pending = not service_rows and not health_rows and warnings == 0
            self._all_clear.setVisible(has_inventory and nothing_pending)
        finally:
            session.close()
