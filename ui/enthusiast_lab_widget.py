"""Optionales Enthusiasten-Lab.

Normale Nutzer müssen diese Ansicht nicht verwenden. Sammler bekommen hier
Restmengen, Farblücken, Feder-Tausch-Historie und Reinigungsstatistik an einem
Ort, ohne die Basisformulare zu überladen.
"""
from __future__ import annotations

from datetime import datetime, time

from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget, QDialog,
    QFormLayout, QComboBox, QDateEdit, QSpinBox,
    QTextEdit, QMessageBox, QGroupBox, QMenu, QApplication,
)

from database.db import get_session
from database.models import Ink, Pen, Nib, PenNibSetup, CleaningLog
from i18n.translator import t, format_date
from logic.enthusiast_lab_service import (
    ink_stock_rows,
    color_gap_rows,
    nib_history_rows,
    cleaning_stats_rows,
)
from logic.event_bus import AppEventBus
from ui.theme import BTN_PRIMARY
from ui.locale_widgets import LocalizedDoubleSpinBox as QDoubleSpinBox
from ui.ui_scale import scale_px


def _fmt_num(value, digits: int = 1) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return "—"


def _label_pen(pen: Pen | None) -> str:
    return f"{pen.brand} {pen.model}".strip() if pen else "—"


def _label_ink(ink: Ink | None) -> str:
    return f"{ink.brand} {ink.name}".strip() if ink else "—"


def _label_nib(nib: Nib | None) -> str:
    if not nib:
        return "—"
    return getattr(nib, "display_label", None) or " ".join(str(x) for x in [nib.manufacturer, nib.physical_size, nib.size] if x) or f"#{nib.id}"


class EnthusiastLabWidget(QWidget):
    # Rechtsklick „Zur Tinte springen" navigiert (Auto-Wiring im Hauptfenster).
    navigate_to = Signal(int)

    def __init__(self):
        super().__init__()
        self._setup_ui()
        bus = AppEventBus.instance()
        bus.inks_changed.connect(self.refresh)
        bus.pens_changed.connect(self.refresh)
        bus.nibs_changed.connect(self.refresh)
        bus.samples_changed.connect(self.refresh)
        bus.all_changed.connect(self.refresh)
        self.refresh()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel(t("enthusiast_lab.title"))
        title.setObjectName("page_title")
        header.addWidget(title)
        header.addStretch()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(t("enthusiast_lab.search_placeholder"))
        self.search_edit.textChanged.connect(self._filter_all)
        header.addWidget(self.search_edit)
        root.addLayout(header)

        hint = QLabel(t("enthusiast_lab.hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#7f8c8d; border:none; padding:2px;")
        root.addWidget(hint)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        self.ink_table = self._make_table([
            "ink", "remaining", "bottle", "fill", "status", "recommendation", "threshold",
        ], "ink_stock")
        self.ink_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.ink_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.ink_table.customContextMenuRequested.connect(self._ink_context_menu)
        ink_page = self._page_with_table(self.ink_table, [
            ("enthusiast_lab.ink_stock.update", self._edit_ink_stock, True),
        ])
        self.tabs.addTab(ink_page, t("enthusiast_lab.tabs.ink_stock"))

        self.color_table = self._make_table([
            "family", "owned", "status", "recommendation", "examples",
        ], "color_gaps")
        self.tabs.addTab(self._page_with_table(self.color_table), t("enthusiast_lab.tabs.color_gaps"))

        self.nib_table = self._make_table([
            "pen", "nib", "installed", "removed", "active", "days", "notes",
        ], "nib_history")
        self.tabs.addTab(self._page_with_table(self.nib_table), t("enthusiast_lab.tabs.nib_history"))

        cleaning_page = QWidget()
        cleaning_layout = QVBoxLayout(cleaning_page)
        cleaning_layout.setContentsMargins(0, 0, 0, 0)
        cleaning_layout.setSpacing(10)
        btn_row = QHBoxLayout()
        add_cleaning = QPushButton(t("enthusiast_lab.cleaning.add"))
        add_cleaning.setStyleSheet(BTN_PRIMARY)
        add_cleaning.clicked.connect(self._add_cleaning_log)
        btn_row.addWidget(add_cleaning)
        btn_row.addStretch()
        cleaning_layout.addLayout(btn_row)
        self.cleaning_stats_table = self._make_table([
            "ink", "count", "avg_minutes", "avg_difficulty", "avg_cycles", "last", "status",
        ], "cleaning_stats")
        self.cleaning_log_table = self._make_table([
            "date", "pen", "ink", "minutes", "difficulty", "cycles", "cleaner", "result", "notes",
        ], "cleaning_logs")
        cleaning_layout.addWidget(QLabel(t("enthusiast_lab.cleaning.stats_title")))
        cleaning_layout.addWidget(self.cleaning_stats_table, 1)
        cleaning_layout.addWidget(QLabel(t("enthusiast_lab.cleaning.logs_title")))
        cleaning_layout.addWidget(self.cleaning_log_table, 1)
        self.tabs.addTab(cleaning_page, t("enthusiast_lab.tabs.cleaning"))

    def _page_with_table(self, table: QTableWidget, actions: list[tuple[str, object, bool]] | None = None) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        if actions:
            row = QHBoxLayout()
            for key, slot, primary in actions:
                btn = QPushButton(t(key))
                if primary:
                    btn.setStyleSheet(BTN_PRIMARY)
                btn.clicked.connect(slot)
                row.addWidget(btn)
            row.addStretch()
            layout.addLayout(row)
        layout.addWidget(table)
        return page

    def _make_table(self, columns: list[str], group: str) -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels([t(f"enthusiast_lab.headers.{group}.{c}") for c in columns])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        return table

    def refresh(self) -> None:
        session = get_session()
        try:
            inks = session.query(Ink).order_by(Ink.brand, Ink.name).all()
            pens = session.query(Pen).order_by(Pen.brand, Pen.model).all()
            setups = session.query(PenNibSetup).order_by(PenNibSetup.installed_date.desc()).all()
            logs = session.query(CleaningLog).order_by(CleaningLog.cleaned_at.desc()).all()
            self._populate_ink_stock(ink_stock_rows(inks))
            self._populate_color_gaps(color_gap_rows(inks))
            self._populate_nib_history(nib_history_rows(pens, setups))
            self._populate_cleaning_stats(cleaning_stats_rows(logs, inks))
            self._populate_cleaning_logs(logs)
            self._filter_all(self.search_edit.text())
        finally:
            session.close()

    def _set_item(self, table: QTableWidget, row: int, col: int, value: str, data=None) -> None:
        item = QTableWidgetItem(value if value not in (None, "") else "—")
        if data is not None:
            item.setData(Qt.ItemDataRole.UserRole, data)
        table.setItem(row, col, item)

    def _populate_ink_stock(self, rows) -> None:
        self.ink_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            values = [
                row.label,
                _fmt_num(row.remaining_ml),
                _fmt_num(row.bottle_size_ml),
                "—" if row.fill_pct is None else f"{row.fill_pct:.0f}%",
                t(f"enthusiast_lab.status.ink.{row.status}"),
                t(f"enthusiast_lab.recommendations.ink.{row.recommendation}"),
                _fmt_num(row.threshold_ml),
            ]
            for c, value in enumerate(values):
                self._set_item(self.ink_table, r, c, value, row.ink_id if c == 0 else None)

    def _populate_color_gaps(self, rows) -> None:
        self.color_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            values = [
                t(f"enthusiast_lab.color_families.{row.family}"),
                str(row.owned_count),
                t(f"enthusiast_lab.status.color.{row.status}"),
                t(f"enthusiast_lab.recommendations.color.{row.recommendation}"),
                ", ".join(row.examples) or "—",
            ]
            for c, value in enumerate(values):
                self._set_item(self.color_table, r, c, value)

    def _populate_nib_history(self, rows) -> None:
        self.nib_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            values = [
                row.pen_label,
                row.nib_label,
                format_date(row.installed_date) if row.installed_date else "—",
                format_date(row.removed_date) if row.removed_date else "—",
                t("common.yes") if row.active else t("common.no"),
                "—" if row.days_installed is None else str(row.days_installed),
                row.notes or "—",
            ]
            for c, value in enumerate(values):
                self._set_item(self.nib_table, r, c, value)

    def _populate_cleaning_stats(self, rows) -> None:
        self.cleaning_stats_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            values = [
                row.ink_label,
                str(row.cleanings),
                _fmt_num(row.avg_minutes),
                _fmt_num(row.avg_difficulty),
                _fmt_num(row.avg_flush_cycles),
                format_date(row.last_cleaned_at) if row.last_cleaned_at else "—",
                t(f"enthusiast_lab.status.cleaning.{row.status}"),
            ]
            for c, value in enumerate(values):
                self._set_item(self.cleaning_stats_table, r, c, value)

    def _populate_cleaning_logs(self, logs: list[CleaningLog]) -> None:
        self.cleaning_log_table.setRowCount(len(logs))
        for r, log in enumerate(logs):
            values = [
                format_date(log.cleaned_at) if log.cleaned_at else "—",
                _label_pen(log.pen),
                _label_ink(log.ink),
                _fmt_num(log.duration_minutes),
                f"{log.difficulty_level}/5" if log.difficulty_level else "—",
                str(log.flush_cycles) if log.flush_cycles is not None else "—",
                log.cleaner_used or "—",
                log.result or "—",
                log.notes or "—",
            ]
            for c, value in enumerate(values):
                self._set_item(self.cleaning_log_table, r, c, value)

    def _filter_all(self, text: str) -> None:
        text = (text or "").strip().lower()
        for table in (self.ink_table, self.color_table, self.nib_table, self.cleaning_stats_table, self.cleaning_log_table):
            for row in range(table.rowCount()):
                visible = not text or any(
                    table.item(row, col) and text in table.item(row, col).text().lower()
                    for col in range(table.columnCount())
                )
                table.setRowHidden(row, not visible)

    def _selected_ink_id(self) -> int | None:
        row = self.ink_table.currentRow()
        if row < 0:
            return None
        item = self.ink_table.item(row, 0)
        return int(item.data(Qt.ItemDataRole.UserRole)) if item and item.data(Qt.ItemDataRole.UserRole) else None

    def _ink_context_menu(self, pos) -> None:
        """Rechtsklick auf die Tinten-Restmengen-Tabelle."""
        item = self.ink_table.itemAt(pos)
        row = item.row() if item is not None else -1
        ink_id = None
        if row >= 0:
            first = self.ink_table.item(row, 0)
            ink_id = first.data(Qt.ItemDataRole.UserRole) if first else None

        menu = QMenu(self)
        act_jump = menu.addAction(t("dashboard.context.jump_to_ink"))
        act_jump.setEnabled(ink_id is not None)
        act_edit = menu.addAction(t("enthusiast_lab.ink_stock.update"))
        act_edit.setEnabled(row >= 0)
        menu.addSeparator()
        act_copy = menu.addAction(t("dashboard.context.copy_details"))
        act_copy.setEnabled(row >= 0)

        chosen = menu.exec(self.ink_table.viewport().mapToGlobal(pos))
        if chosen is act_jump and ink_id is not None:
            self.navigate_to.emit(2)
        elif chosen is act_edit:
            self._edit_ink_stock()
        elif chosen is act_copy and row >= 0:
            cells = []
            for col in range(self.ink_table.columnCount()):
                cell = self.ink_table.item(row, col)
                if cell and cell.text():
                    cells.append(cell.text())
            clip = QApplication.clipboard()
            if clip is not None:
                clip.setText(" · ".join(cells))

    def _edit_ink_stock(self) -> None:
        ink_id = self._selected_ink_id()
        if ink_id is None:
            QMessageBox.information(self, t("common.info"), t("enthusiast_lab.ink_stock.select_first"))
            return
        session = get_session()
        try:
            ink = session.get(Ink, ink_id)
            if ink is None:
                return
            dlg = InkStockDialog(self, ink=ink)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                data = dlg.get_data()
                ink.remaining_ml = data["remaining_ml"]
                ink.reorder_threshold_ml = data["reorder_threshold_ml"]
                ink.reorder_url = data["reorder_url"]
                ink.reorder_note = data["reorder_note"]
                ink.is_empty = bool(data["is_empty"])
                session.commit()
                AppEventBus.instance().emit_inks()
                self.refresh()
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, t("common.error"), str(exc))
        finally:
            session.close()

    def _add_cleaning_log(self) -> None:
        session = get_session()
        try:
            dlg = CleaningLogDialog(self, session=session)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                log = CleaningLog(**dlg.get_data())
                session.add(log)
                session.commit()
                AppEventBus.instance().emit_all()
                self.refresh()
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, t("common.error"), str(exc))
        finally:
            session.close()


class InkStockDialog(QDialog):
    def __init__(self, parent=None, *, ink: Ink):
        super().__init__(parent)
        self.setWindowTitle(t("enthusiast_lab.ink_stock.dialog_title"))
        self.setMinimumWidth(scale_px(420))
        root = QVBoxLayout(self)
        form_box = QGroupBox(_label_ink(ink))
        form = QFormLayout(form_box)
        self.remaining = QDoubleSpinBox(); self.remaining.setRange(0, 10000); self.remaining.setDecimals(1); self.remaining.setSuffix(" ml")
        self.threshold = QDoubleSpinBox(); self.threshold.setRange(0, 10000); self.threshold.setDecimals(1); self.threshold.setSuffix(" ml")
        self.url = QLineEdit()
        self.note = QTextEdit(); self.note.setMinimumHeight(scale_px(70))
        self.empty = QComboBox(); self.empty.addItem(t("common.no"), False); self.empty.addItem(t("common.yes"), True)
        self.remaining.setValue(float(ink.remaining_ml or 0))
        self.threshold.setValue(float(ink.reorder_threshold_ml or 5))
        self.url.setText(ink.reorder_url or "")
        self.note.setPlainText(ink.reorder_note or "")
        self.empty.setCurrentIndex(1 if ink.is_empty else 0)
        form.addRow(t("enthusiast_lab.ink_stock.remaining"), self.remaining)
        form.addRow(t("enthusiast_lab.ink_stock.threshold"), self.threshold)
        form.addRow(t("enthusiast_lab.ink_stock.url"), self.url)
        form.addRow(t("enthusiast_lab.ink_stock.note"), self.note)
        form.addRow(t("enthusiast_lab.ink_stock.empty"), self.empty)
        root.addWidget(form_box)
        buttons = QHBoxLayout(); buttons.addStretch()
        save = QPushButton(t("common.save")); cancel = QPushButton(t("common.cancel"))
        save.clicked.connect(self.accept); cancel.clicked.connect(self.reject)
        buttons.addWidget(save); buttons.addWidget(cancel); root.addLayout(buttons)

    def get_data(self) -> dict:
        return {
            "remaining_ml": self.remaining.value(),
            "reorder_threshold_ml": self.threshold.value(),
            "reorder_url": self.url.text().strip() or None,
            "reorder_note": self.note.toPlainText().strip() or None,
            "is_empty": bool(self.empty.currentData()),
        }


class CleaningLogDialog(QDialog):
    def __init__(self, parent=None, *, session):
        super().__init__(parent)
        self.session = session
        self.setWindowTitle(t("enthusiast_lab.cleaning.dialog_title"))
        self.setMinimumWidth(scale_px(520))
        root = QVBoxLayout(self)
        form = QFormLayout()
        self.date = QDateEdit(); self.date.setCalendarPopup(True); self.date.setDate(QDate.currentDate())
        self.pen = QComboBox(); self.ink = QComboBox()
        self.pen.addItem(t("enthusiast_lab.optional_none"), None)
        for pen in session.query(Pen).order_by(Pen.brand, Pen.model).all():
            self.pen.addItem(_label_pen(pen), pen.id)
        self.ink.addItem(t("enthusiast_lab.optional_none"), None)
        for ink in session.query(Ink).order_by(Ink.brand, Ink.name).all():
            self.ink.addItem(_label_ink(ink), ink.id)
        self.minutes = QDoubleSpinBox(); self.minutes.setRange(0, 600); self.minutes.setDecimals(1); self.minutes.setSuffix(" min")
        self.difficulty = QSpinBox(); self.difficulty.setRange(1, 5); self.difficulty.setValue(3)
        self.cycles = QSpinBox(); self.cycles.setRange(0, 100); self.cycles.setValue(0)
        self.cleaner = QLineEdit(); self.cleaner.setPlaceholderText(t("enthusiast_lab.cleaning.cleaner_placeholder"))
        self.result = QComboBox()
        for key in ("clean", "stained", "needs_repeat"):
            self.result.addItem(t(f"enthusiast_lab.cleaning.results.{key}"), key)
        self.notes = QTextEdit(); self.notes.setMinimumHeight(scale_px(80))
        form.addRow(t("enthusiast_lab.cleaning.fields.date"), self.date)
        form.addRow(t("enthusiast_lab.cleaning.fields.pen"), self.pen)
        form.addRow(t("enthusiast_lab.cleaning.fields.ink"), self.ink)
        form.addRow(t("enthusiast_lab.cleaning.fields.minutes"), self.minutes)
        form.addRow(t("enthusiast_lab.cleaning.fields.difficulty"), self.difficulty)
        form.addRow(t("enthusiast_lab.cleaning.fields.cycles"), self.cycles)
        form.addRow(t("enthusiast_lab.cleaning.fields.cleaner"), self.cleaner)
        form.addRow(t("enthusiast_lab.cleaning.fields.result"), self.result)
        form.addRow(t("enthusiast_lab.cleaning.fields.notes"), self.notes)
        root.addLayout(form)
        buttons = QHBoxLayout(); buttons.addStretch()
        save = QPushButton(t("common.save")); cancel = QPushButton(t("common.cancel"))
        save.clicked.connect(self.accept); cancel.clicked.connect(self.reject)
        buttons.addWidget(save); buttons.addWidget(cancel); root.addLayout(buttons)

    def get_data(self) -> dict:
        qdate = self.date.date()
        cleaned_at = datetime.combine(datetime(qdate.year(), qdate.month(), qdate.day()).date(), time.min)
        return {
            "cleaned_at": cleaned_at,
            "pen_id": self.pen.currentData(),
            "ink_id": self.ink.currentData(),
            "duration_minutes": self.minutes.value() or None,
            "difficulty_level": self.difficulty.value(),
            "flush_cycles": self.cycles.value() or None,
            "cleaner_used": self.cleaner.text().strip() or None,
            "result": self.result.currentData(),
            "notes": self.notes.toPlainText().strip() or None,
        }
