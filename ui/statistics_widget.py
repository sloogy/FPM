"""Statistik-Modul: Ausgaben- und Nutzungsübersicht.

v0.2.50:
- Scrollbarer Statistikbereich
- dynamische Jahr-/Monatsauswahl je Zeitraum
- separater Zeitraum für Füller- und Tintenranking
- Durchschnitt pro Ausgabe
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Iterable

from PySide6.QtCore import QDate, QLocale, Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QDateEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QSplitter, QScrollArea, QFrame, QFileDialog, QPushButton, QMessageBox,
)

from pathlib import Path
from database.db import get_session
from database.models import AppSettings, Expense, Ink, InkLoad, Pen
from i18n.translator import LocaleService, Translator, format_money, format_number, format_date, t
from logic.event_bus import AppEventBus
from logic.statistics_service import (
    summarize_expenses, rank_usage, period_bounds,
    collection_value_summary, value_by_year, budget_status, stale_ranking,
    build_insurance_rows, build_statistics_csv_rows,
)


EXPENSE_FILTER_TYPES = [
    "pen", "ink", "nib", "paper", "accessory", "service", "shipping", "customs", "other",
]


def _as_date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def _qt_date_to_date(value: QDate) -> date:
    return date(value.year(), value.month(), value.day())


def _date_to_qdate(value: date) -> QDate:
    return QDate(value.year, value.month, value.day)


def _item_type_label(key: str | None) -> str:
    return t(f"expenses.categories.{key}") if key else t("ui.statistics_widget.all_categories")


def _month_locale() -> QLocale:
    lang = Translator.instance().language
    mapping = {
        "de": QLocale(QLocale.Language.German, QLocale.Country.Switzerland),
        "en": QLocale(QLocale.Language.English),
        "fr": QLocale(QLocale.Language.French),
    }
    return mapping.get(lang, QLocale(QLocale.Language.German, QLocale.Country.Switzerland))


def _set_card_value(card: QWidget, value: str) -> None:
    label = card.findChild(QLabel, "statsCardValue")
    if label:
        label.setText(value)


def _card(value: str, label: str) -> QWidget:
    widget = QWidget()
    widget.setObjectName("summaryCard")
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(12, 10, 12, 10)
    value_label = QLabel(value)
    value_label.setObjectName("statsCardValue")
    value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    value_label.setStyleSheet("font-size:22px;font-weight:bold;border:none;")
    text_label = QLabel(label)
    text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    text_label.setObjectName("summaryLabel")
    text_label.setWordWrap(True)
    layout.addWidget(value_label)
    layout.addWidget(text_label)
    return widget


class _PeriodSelector(QWidget):
    """Dynamischer Zeitraum-Selector für Overall/Jahr/Monat/Woche.

    Statt eines einzelnen Stichtag-Felds zeigt der Selector nur die Eingaben an,
    die für den gewählten Zeitraum wirklich gebraucht werden. Die Datenlogik
    bleibt trotzdem bei ``period_bounds()`` aus ``logic.statistics_service``.
    """

    changed = Signal()

    def __init__(self, *, include_week: bool = False, default_period: str = "overall", parent=None):
        super().__init__(parent)
        self._include_week = include_week
        self._default_period = default_period
        self._setup_ui()

    def _setup_ui(self) -> None:
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        row.addWidget(QLabel(t("ui.statistics_widget.period")))
        self.period_combo = QComboBox()
        self.period_combo.addItem(t("ui.statistics_widget.overall"), "overall")
        self.period_combo.addItem(t("ui.statistics_widget.year"), "year")
        self.period_combo.addItem(t("ui.statistics_widget.month"), "month")
        if self._include_week:
            self.period_combo.addItem(t("ui.statistics_widget.week"), "week")
        default_idx = self.period_combo.findData(self._default_period)
        self.period_combo.setCurrentIndex(default_idx if default_idx >= 0 else 0)
        self.period_combo.currentIndexChanged.connect(self._on_period_changed)
        row.addWidget(self.period_combo)

        self.year_combo = QComboBox()
        self.year_combo.currentIndexChanged.connect(lambda *_: self.changed.emit())
        row.addWidget(self.year_combo)

        self.month_combo = QComboBox()
        self._populate_months()
        self.month_combo.setCurrentIndex(date.today().month - 1)
        self.month_combo.currentIndexChanged.connect(lambda *_: self.changed.emit())
        row.addWidget(self.month_combo)

        self.week_date = QDateEdit(QDate.currentDate())
        self.week_date.setCalendarPopup(True)
        self.week_date.setDisplayFormat(LocaleService.instance().qt_date_format)
        self.week_date.dateChanged.connect(lambda *_: self.changed.emit())
        row.addWidget(self.week_date)

        row.addStretch(1)
        self.set_years([date.today().year])
        self._on_period_changed(emit=False)

    def _populate_months(self) -> None:
        current = self.month_combo.currentData() if hasattr(self, "month_combo") else None
        loc = _month_locale()
        self.month_combo.blockSignals(True)
        self.month_combo.clear()
        for month in range(1, 13):
            self.month_combo.addItem(loc.monthName(month, QLocale.FormatType.LongFormat), month)
        idx = self.month_combo.findData(current)
        self.month_combo.setCurrentIndex(idx if idx >= 0 else date.today().month - 1)
        self.month_combo.blockSignals(False)

    def set_years(self, years: Iterable[int]) -> None:
        normalized = sorted({int(y) for y in years if y}, reverse=True)
        if not normalized:
            normalized = [date.today().year]
        previous = self.year_combo.currentData()
        self.year_combo.blockSignals(True)
        self.year_combo.clear()
        for year in normalized:
            self.year_combo.addItem(str(year), year)
        idx = self.year_combo.findData(previous)
        if idx < 0:
            idx = self.year_combo.findData(date.today().year)
        self.year_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.year_combo.blockSignals(False)

    def refresh_locale(self) -> None:
        self.week_date.setDisplayFormat(LocaleService.instance().qt_date_format)
        self._populate_months()

    def period(self) -> str:
        return self.period_combo.currentData() or "overall"

    def reference_date(self) -> date:
        period = self.period()
        if period == "year":
            year = self.year_combo.currentData() or date.today().year
            return date(int(year), 1, 1)
        if period == "month":
            year = self.year_combo.currentData() or date.today().year
            month = self.month_combo.currentData() or date.today().month
            return date(int(year), int(month), 1)
        if period == "week":
            return _qt_date_to_date(self.week_date.date())
        return date.today()

    def describe(self) -> str:
        start, end = period_bounds(self.period(), self.reference_date())
        if start is None or end is None:
            return t("ui.statistics_widget.overall")
        return f"{format_date(start)} – {format_date(end - timedelta(days=1))}"

    def _on_period_changed(self, *_args, emit: bool = True) -> None:
        period = self.period()
        self.year_combo.setVisible(period in {"year", "month"})
        self.month_combo.setVisible(period == "month")
        self.week_date.setVisible(period == "week")
        if emit:
            self.changed.emit()


class StatisticsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._setup_ui()
        bus = AppEventBus.instance()
        bus.expenses_changed.connect(self.refresh)
        bus.pens_changed.connect(self.refresh)
        bus.inks_changed.connect(self.refresh)
        bus.all_changed.connect(self.refresh)
        self.refresh()

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        body = QWidget()
        scroll.setWidget(body)
        root = QVBoxLayout(body)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel(t("ui.statistics_widget.title"))
        title.setObjectName("page_title")
        header.addWidget(title)
        header.addStretch(1)
        refresh_btn = QPushButton(t("ui.statistics_widget.refresh"))
        refresh_btn.clicked.connect(self.refresh)
        header.addWidget(refresh_btn)
        root.addLayout(header)

        root.addWidget(self._build_expense_section())
        root.addWidget(self._build_value_section())
        root.addWidget(self._build_usage_section(), 1)
        root.addLayout(self._build_export_row())

        self.period_hint = QLabel("")
        self.period_hint.setWordWrap(True)
        self.period_hint.setStyleSheet("color:#64748b;border:none;")
        root.addWidget(self.period_hint)
        root.addStretch(1)

    def _build_expense_section(self) -> QGroupBox:
        group = QGroupBox(t("ui.statistics_widget.expense_filters"))
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        filters = QHBoxLayout()
        filters.setSpacing(12)
        self.expense_period = _PeriodSelector(include_week=False, default_period="overall")
        self.expense_period.changed.connect(self.refresh)
        filters.addWidget(self.expense_period, 1)
        filters.addWidget(QLabel(t("ui.statistics_widget.category")))
        self.expense_type = QComboBox()
        self.expense_type.addItem(t("ui.statistics_widget.all_categories"), "")
        for key in EXPENSE_FILTER_TYPES:
            self.expense_type.addItem(_item_type_label(key), key)
        self.expense_type.currentIndexChanged.connect(self.refresh)
        filters.addWidget(self.expense_type)
        layout.addLayout(filters)

        cards = QHBoxLayout()
        cards.setSpacing(10)
        self.expense_total_card = _card("—", t("ui.statistics_widget.expense_total"))
        self.expense_count_card = _card("—", t("ui.statistics_widget.expense_count"))
        self.expense_average_card = _card("—", t("ui.statistics_widget.expense_average"))
        for card in (self.expense_total_card, self.expense_count_card, self.expense_average_card):
            cards.addWidget(card)
        layout.addLayout(cards)

        self.expense_table = self._make_table([
            t("ui.statistics_widget.category"),
            t("ui.statistics_widget.entries"),
            t("ui.statistics_widget.total_default_currency"),
            t("ui.statistics_widget.original_currencies"),
        ])
        self.expense_table.setMinimumHeight(220)
        layout.addWidget(self.expense_table)
        return group

    def _build_value_section(self) -> QGroupBox:
        """Sammlungswert, Budgetampel, Wertentwicklung und Staleness (v0.2.57)."""
        group = QGroupBox(t("ui.statistics_widget.value_section"))
        outer = QVBoxLayout(group)

        cards = QHBoxLayout()
        self.value_purchase_card = _card("—", t("ui.statistics_widget.value_purchase"))
        self.value_market_card = _card("—", t("ui.statistics_widget.value_market"))
        self.value_insurance_card = _card("—", t("ui.statistics_widget.value_insurance"))
        self.value_delta_card = _card("—", t("ui.statistics_widget.value_delta"))
        for c in (self.value_purchase_card, self.value_market_card, self.value_insurance_card, self.value_delta_card):
            cards.addWidget(c)
        outer.addLayout(cards)

        self.budget_label = QLabel("")
        self.budget_label.setWordWrap(True)
        outer.addWidget(self.budget_label)

        tables = QHBoxLayout()
        self.value_year_table = QTableWidget()
        self.value_year_table.setColumnCount(4)
        self.value_year_table.setHorizontalHeaderLabels([
            t("ui.statistics_widget.year_col"),
            t("ui.statistics_widget.purchases_col"),
            t("ui.statistics_widget.sum_col"),
            t("ui.statistics_widget.cumulative_col"),
        ])
        self.value_year_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.value_year_table.verticalHeader().setVisible(False)
        self.value_year_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tables.addWidget(self._wrap_table(t("ui.statistics_widget.value_by_year"), self.value_year_table))

        self.stale_pen_table = QTableWidget()
        self.stale_ink_table = QTableWidget()
        for tbl in (self.stale_pen_table, self.stale_ink_table):
            tbl.setColumnCount(2)
            tbl.setHorizontalHeaderLabels([
                t("ui.statistics_widget.stale_label_col"),
                t("ui.statistics_widget.stale_days_col"),
            ])
            tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            tbl.verticalHeader().setVisible(False)
            tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tables.addWidget(self._wrap_table(t("ui.statistics_widget.stale_pens"), self.stale_pen_table))
        tables.addWidget(self._wrap_table(t("ui.statistics_widget.stale_inks"), self.stale_ink_table))
        outer.addLayout(tables)
        return group

    @staticmethod
    def _wrap_table(title: str, table: QTableWidget) -> QWidget:
        box = QWidget()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        cap = QLabel(title)
        cap.setStyleSheet("font-weight:bold;")
        lay.addWidget(cap)
        lay.addWidget(table)
        return box

    def _build_export_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addStretch(1)
        self.export_stats_btn = QPushButton(t("ui.statistics_widget.export_csv"))
        self.export_stats_btn.clicked.connect(self._export_statistics_csv)
        self.export_insurance_btn = QPushButton(t("ui.statistics_widget.export_insurance"))
        self.export_insurance_btn.clicked.connect(self._export_insurance_csv)
        row.addWidget(self.export_stats_btn)
        row.addWidget(self.export_insurance_btn)
        return row

    def _build_usage_section(self) -> QSplitter:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.pen_period = _PeriodSelector(include_week=True, default_period="week")
        self.pen_period.changed.connect(self.refresh)
        self.top_pen_card = _card("—", t("ui.statistics_widget.top_pen"))
        self.pen_table = self._make_usage_table()
        splitter.addWidget(self._usage_group(
            t("ui.statistics_widget.most_used_pens"),
            self.pen_period,
            self.top_pen_card,
            self.pen_table,
        ))

        self.ink_period = _PeriodSelector(include_week=True, default_period="week")
        self.ink_period.changed.connect(self.refresh)
        self.top_ink_card = _card("—", t("ui.statistics_widget.top_ink"))
        self.ink_table = self._make_usage_table()
        splitter.addWidget(self._usage_group(
            t("ui.statistics_widget.most_used_inks"),
            self.ink_period,
            self.top_ink_card,
            self.ink_table,
        ))
        splitter.setSizes([680, 680])
        return splitter

    @staticmethod
    def _usage_group(title: str, period_selector: QWidget, card: QWidget, table: QTableWidget) -> QGroupBox:
        group = QGroupBox(title)
        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        layout.addWidget(period_selector)
        layout.addWidget(card)
        table.setMinimumHeight(260)
        layout.addWidget(table)
        return group

    @staticmethod
    def _make_table(headers: list[str]) -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        header = table.horizontalHeader()
        for col in range(len(headers)):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        return table

    def _make_usage_table(self) -> QTableWidget:
        table = self._make_table([
            t("ui.statistics_widget.rank"),
            t("ui.statistics_widget.object"),
            t("ui.statistics_widget.usage_days"),
            t("ui.statistics_widget.fills"),
            t("ui.statistics_widget.volume_ml"),
            t("ui.statistics_widget.last_filled"),
        ])
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for col in (2, 3, 4, 5):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        return table

    def refresh(self) -> None:
        if not hasattr(self, "expense_table"):
            return
        session = get_session()
        try:
            expenses = session.query(Expense).all()
            loads = session.query(InkLoad).all()
            locale = LocaleService.instance()
            self._refresh_period_locale()
            self._refresh_year_options(expenses, loads)

            expense_period = self.expense_period.period()
            expense_ref = self.expense_period.reference_date()
            item_type = self.expense_type.currentData() or ""
            selected_types = {item_type} if item_type else None
            expense_stats = summarize_expenses(
                expenses,
                period=expense_period,
                reference=expense_ref,
                item_types=selected_types,
                convert_to_default=locale.convert_to_default,
            )
            self._populate_expense_table(expense_stats)
            _set_card_value(self.expense_total_card, format_money(expense_stats["total_default"], locale.currency))
            _set_card_value(self.expense_count_card, str(expense_stats["count"]))
            _set_card_value(self.expense_average_card, format_money(expense_stats["average_default"], locale.currency))

            pen_period = self.pen_period.period()
            pen_ref = self.pen_period.reference_date()
            ink_period = self.ink_period.period()
            ink_ref = self.ink_period.reference_date()
            pen_rank = rank_usage(loads, kind="pen", period=pen_period, reference=pen_ref)
            ink_rank = rank_usage(loads, kind="ink", period=ink_period, reference=ink_ref)
            self._populate_usage_table(self.pen_table, pen_rank)
            self._populate_usage_table(self.ink_table, ink_rank)
            _set_card_value(self.top_pen_card, self._top_label(pen_rank))
            _set_card_value(self.top_ink_card, self._top_label(ink_rank))
            self._update_period_hint()

            # Collector Insights (v0.2.57)
            pens = session.query(Pen).filter_by(is_active=True).all()
            inks = session.query(Ink).all()
            self._last_expense_stats = expense_stats
            self._last_pen_rank = pen_rank
            self._last_ink_rank = ink_rank
            self._refresh_value_section(session, pens, inks, loads, expenses, locale)
        finally:
            session.close()

    def _refresh_value_section(self, session, pens, inks, loads, expenses, locale) -> None:
        summary = collection_value_summary(pens, convert=locale.convert_to_default)
        self._last_value_summary = summary
        cur = locale.currency
        _set_card_value(self.value_purchase_card, format_money(summary["purchase_total"], cur))
        _set_card_value(self.value_market_card, format_money(summary["market_total"], cur))
        _set_card_value(self.value_insurance_card, format_money(summary["insurance_total"], cur))
        if summary["delta_pct"] is None:
            _set_card_value(self.value_delta_card, "—")
        else:
            sign = "+" if summary["delta"] >= 0 else ""
            _set_card_value(self.value_delta_card, f"{sign}{format_money(summary['delta'], cur)} ({sign}{summary['delta_pct']:.1f}%)")

        # Budgetampel Monat + Jahr
        today = date.today()
        month_spent = summarize_expenses(expenses, period="month", reference=today,
                                         convert_to_default=locale.convert_to_default)["total_default"]
        year_spent = summarize_expenses(expenses, period="year", reference=today,
                                        convert_to_default=locale.convert_to_default)["total_default"]
        try:
            b_month = float(AppSettings.get(session, "budget_monthly", "0") or 0)
            b_year = float(AppSettings.get(session, "budget_yearly", "0") or 0)
        except (TypeError, ValueError):
            b_month = b_year = 0.0
        parts = []
        colors = {"ok": "#27ae60", "warn": "#e67e22", "over": "#e74c3c"}
        worst = "none"
        for label_key, status in (("budget_month", budget_status(month_spent, b_month)),
                                  ("budget_year", budget_status(year_spent, b_year))):
            if status["level"] == "none":
                continue
            parts.append(t(f"ui.statistics_widget.{label_key}",
                           spent=format_money(status["spent"], cur),
                           budget=format_money(status["budget"], cur),
                           pct=f"{status['pct']:.0f}"))
            order = ["none", "ok", "warn", "over"]
            if order.index(status["level"]) > order.index(worst):
                worst = status["level"]
        if parts:
            self.budget_label.setText("  ·  ".join(parts))
            self.budget_label.setStyleSheet(f"font-weight:bold;color:{colors.get(worst, '#2c3e50')};")
        else:
            self.budget_label.setText(t("ui.statistics_widget.budget_unset"))
            self.budget_label.setStyleSheet("color:#7f8c8d;")

        # Wertentwicklung nach Jahr
        year_rows = value_by_year(pens, convert=locale.convert_to_default)
        self.value_year_table.setRowCount(len(year_rows))
        for r, row in enumerate(year_rows):
            vals = [str(row["year"]), str(row["count"]),
                    format_money(row["purchase_total"], cur), format_money(row["cumulative_total"], cur)]
            for c, v in enumerate(vals):
                self.value_year_table.setItem(r, c, QTableWidgetItem(v))

        # Lange ungenutzt (Top 8)
        for tbl, entities, kind in ((self.stale_pen_table, pens, "pen"), (self.stale_ink_table, inks, "ink")):
            rows = stale_ranking(entities, loads, kind=kind, limit=8)
            tbl.setRowCount(len(rows))
            for r, row in enumerate(rows):
                days = t("ui.statistics_widget.stale_never") if row["never"] else t("ui.statistics_widget.stale_days", days=row["days"])
                tbl.setItem(r, 0, QTableWidgetItem(row["label"]))
                tbl.setItem(r, 1, QTableWidgetItem(days))

    def _export_statistics_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, t("ui.statistics_widget.export_csv"),
                                              str(Path.home() / "fpm_statistik.csv"), "CSV (*.csv)")
        if not path:
            return
        rows = build_statistics_csv_rows(
            getattr(self, "_last_expense_stats", {"total_default": 0, "count": 0, "by_type": {}}),
            getattr(self, "_last_pen_rank", []),
            getattr(self, "_last_ink_rank", []),
            getattr(self, "_last_value_summary", {}),
        )
        self._write_csv(path, rows)

    def _export_insurance_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, t("ui.statistics_widget.export_insurance"),
                                              str(Path.home() / "fpm_versicherungsliste.csv"), "CSV (*.csv)")
        if not path:
            return
        session = get_session()
        try:
            pens = session.query(Pen).filter_by(is_active=True).all()
            rows = build_insurance_rows(pens)
        finally:
            session.close()
        self._write_csv(path, rows)

    def _write_csv(self, path: str, rows: list) -> None:
        import csv
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as fh:
                csv.writer(fh, delimiter=";").writerows(rows)
        except OSError as exc:
            QMessageBox.warning(self, t("ui.statistics_widget.export_failed_title"),
                                t("ui.statistics_widget.export_failed_body", error=str(exc)))
            return
        QMessageBox.information(self, t("ui.statistics_widget.export_done_title"),
                                t("ui.statistics_widget.export_done_body", path=path))

    def _refresh_period_locale(self) -> None:
        for selector in (self.expense_period, self.pen_period, self.ink_period):
            selector.refresh_locale()

    def _refresh_year_options(self, expenses: list[Expense], loads: list[InkLoad]) -> None:
        expense_years = [d.year for d in (_as_date(getattr(exp, "purchase_date", None)) for exp in expenses) if d]
        load_years: list[int] = []
        for load in loads:
            for attr in ("loaded_date", "cleaned_date"):
                d = _as_date(getattr(load, attr, None))
                if d:
                    load_years.append(d.year)
        self.expense_period.set_years(expense_years)
        self.pen_period.set_years(load_years)
        self.ink_period.set_years(load_years)

    def _format_currency_map(self, mapping: dict[str, float]) -> str:
        if not mapping:
            return "—"
        return " / ".join(format_money(value, currency) for currency, value in sorted(mapping.items()))

    def _populate_expense_table(self, stats: dict) -> None:
        rows = sorted(
            stats["by_type"].values(),
            key=lambda row: row["total_default"],
            reverse=True,
        )
        self.expense_table.setRowCount(len(rows))
        locale = LocaleService.instance()
        for row_idx, row in enumerate(rows):
            values = [
                _item_type_label(row["item_type"]),
                str(row["count"]),
                format_money(row["total_default"], locale.currency),
                self._format_currency_map(row["by_currency"]),
            ]
            for col, value in enumerate(values):
                self.expense_table.setItem(row_idx, col, QTableWidgetItem(value))

    def _populate_usage_table(self, table: QTableWidget, rows: list[dict]) -> None:
        table.setRowCount(len(rows))
        for row_idx, row in enumerate(rows):
            last_loaded = row.get("last_loaded")
            values = [
                str(row_idx + 1),
                row.get("label") or "—",
                str(row.get("usage_days") or 0),
                str(row.get("fill_count") or 0),
                format_number(float(row.get("volume_ml") or 0.0), 2),
                format_date(last_loaded) if last_loaded else "—",
            ]
            for col, value in enumerate(values):
                table.setItem(row_idx, col, QTableWidgetItem(value))

    @staticmethod
    def _top_label(rows: list[dict]) -> str:
        if not rows:
            return "—"
        first = rows[0]
        days = first.get("usage_days") or 0
        fills = first.get("fill_count") or 0
        return t(
            "ui.statistics_widget.top_usage_value",
            label=first.get("label") or "—",
            days=days,
            fills=fills,
        )

    def _update_period_hint(self) -> None:
        self.period_hint.setText(
            t(
                "ui.statistics_widget.period_hint_separate",
                expense_period=self.expense_period.describe(),
                pen_period=self.pen_period.describe(),
                ink_period=self.ink_period.describe(),
            )
        )
