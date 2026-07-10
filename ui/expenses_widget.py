"""
Ausgaben-Tracker – vollständiger Einkaufs-, Service- und Sammlerwert-Überblick.

v0.2.7:
- Ausgabe bearbeiten statt nur löschen
- CHF/EUR/USD wählbar
- Händler, Bestellnummer, Zahlungsart, Garantie bis
- Verknüpfung mit Füller/Tinte/Feder/Papier
- Kategorie-Filter + Summen pro Währung
- Servicekosten aus Füller-Service bleiben kompatibel
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QDialog, QFormLayout, QComboBox, QDoubleSpinBox, QDateEdit,
    QTextEdit, QGroupBox, QMessageBox, QMenu, QCheckBox, QSplitter,
    QFrame, QScrollArea, QStackedWidget
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor

from ui.ui_scale import scale_px
from ui.common import EmptyStateWidget
from database.db import get_session
from database.models import Expense, Pen, Ink, Nib, Paper
from i18n.translator import LocaleService, format_money, format_date, t
from logic.event_bus import AppEventBus
from logic.budget_export_service import sync_default_outbox_from_session

ITEM_TYPE_KEYS = ["pen", "ink", "nib", "service", "paper", "accessory", "shipping", "customs", "other"]

def _item_types():
    return [(key, t(f"expenses.categories.{key}")) for key in ITEM_TYPE_KEYS]

def _item_type_label(key: str | None) -> str:
    return dict(_item_types()).get(key, key or "—")

CURRENCIES = ["CHF", "EUR", "USD", "GBP"]
PAYMENT_METHOD_KEYS = ["empty", "card", "paypal", "twint", "bank_transfer", "cash", "invoice", "other"]

def _payment_methods():
    return [t(f"expenses.payment.{key}") for key in PAYMENT_METHOD_KEYS]



def _sync_pen_values_from_expenses(session, pen_id: int | None):
    """Verknüpfte Ausgaben zurück an den Füller schreiben.

    Kaufwert = Summe aller Ausgaben der Kategorie "pen" für diesen Füller.
    Servicekosten = Summe aller Ausgaben der Kategorie "service" für diesen Füller.
    Damit ist der Ausgaben-Tracker die Quelle der Wahrheit und der Füller bleibt aktuell.
    """
    if not pen_id:
        return
    pen = session.get(Pen, pen_id)
    if not pen:
        return
    rows = session.query(Expense).filter(Expense.pen_id == pen_id).all()
    lc = LocaleService.instance()
    purchase_rows = [e for e in rows if e.item_type == "pen"]
    service_rows = [e for e in rows if e.item_type == "service"]
    purchase_total = sum(lc.convert_to_default(e.total or 0.0, e.currency or lc.currency) for e in purchase_rows)
    service_total = sum(lc.convert_to_default(e.total or 0.0, e.currency or lc.currency) for e in service_rows)
    pen.purchase_price = purchase_total or None
    pen.purchase_currency = lc.currency
    pen.service_cost = service_total or None
    pen.service_currency = lc.currency


def _money(amount: float | None, currency: str = None) -> str:
    return format_money(amount or 0.0, currency or LocaleService.instance().currency)


class ExpensesWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._setup_ui()
        AppEventBus.instance().expenses_changed.connect(self.refresh)
        self.refresh()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(14)

        hdr = QHBoxLayout()
        title = QLabel(t('ui.expenses_widget.ausgaben_tracker_604689b7'))
        title.setObjectName("page_title")
        hdr.addWidget(title)
        hdr.addStretch()

        self.category_filter = QComboBox()
        self.category_filter.addItem(t('ui.expenses_widget.alle_kategorien_b65c1f8b'), "")
        for val, lbl in _item_types():
            self.category_filter.addItem(lbl, val)
        self.category_filter.currentIndexChanged.connect(self._filter)
        hdr.addWidget(self.category_filter)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(t('ui.expenses_widget.suchen_handler_beschreibung_bestellung_2f55aa68'))
        self.search_edit.setMinimumWidth(scale_px(300))
        self.search_edit.textChanged.connect(self._filter)
        hdr.addWidget(self.search_edit)

        add_btn = QPushButton(t('ui.expenses_widget.ausgabe_c7d8b984'))
        add_btn.setProperty("class", "primary")
        add_btn.clicked.connect(self._add)
        hdr.addWidget(add_btn)
        root.addLayout(hdr)

        self._summary_row = QHBoxLayout(); self._summary_row.setSpacing(10)
        self._total_lbl   = self._summary_card("—", t("expenses.summary.total"))
        self._pens_lbl    = self._summary_card("—", t("expenses.summary.pens"))
        self._inks_lbl    = self._summary_card("—", t("expenses.summary.inks"))
        self._nibs_lbl    = self._summary_card("—", t("expenses.summary.nibs"))
        self._paper_lbl   = self._summary_card("—", t("expenses.summary.paper"))
        self._service_lbl = self._summary_card("—", t("expenses.summary.service"))
        self._other_lbl   = self._summary_card("—", t("expenses.summary.rest"))
        for c in (self._total_lbl, self._pens_lbl, self._inks_lbl, self._nibs_lbl, self._paper_lbl, self._service_lbl, self._other_lbl):
            self._summary_row.addWidget(c)
        root.addLayout(self._summary_row)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget(); ll = QVBoxLayout(left); ll.setContentsMargins(0,0,0,0)
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([t('ui.expenses_widget.datum_441afa63'), t('ui.expenses_widget.kategorie_a2aa2e02'), t('ui.expenses_widget.objekt_f7951b6e'), t('ui.expenses_widget.beschreibung_3c599e40'), t('ui.expenses_widget.handler_8b886ac0'), t('ui.expenses_widget.betrag_9c95a748'), t('ui.expenses_widget.versand_681fd4b2'), t('ui.expenses_widget.zoll_532508a1'), t('ui.expenses_widget.gesamt_edc5a63c')])
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        for i in (5,6,7,8): hh.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        self.table.clicked.connect(self._on_select)
        self.table.doubleClicked.connect(self._edit)

        # Einheitlicher Leerzustand statt blanker Tabelle.
        self.stack = QStackedWidget()
        self.stack.addWidget(self.table)                    # index 0
        self._empty_state = EmptyStateWidget(
            icon="💰",
            title=t("ui.expenses_widget.empty_title"),
            subtitle=t("ui.expenses_widget.empty_subtitle"),
            action_label=t("ui.expenses_widget.empty_action"),
            action_slot=self._add,
        )
        self.stack.addWidget(self._empty_state)             # index 1
        ll.addWidget(self.stack)

        btn_row = QHBoxLayout()
        self.edit_btn = QPushButton(t('ui.expenses_widget.bearbeiten_3a325b55')); self.edit_btn.setEnabled(False); self.edit_btn.setProperty("class", "warning"); self.edit_btn.clicked.connect(self._edit)
        self.del_btn = QPushButton(t('ui.expenses_widget.loschen_1e444093')); self.del_btn.setEnabled(False); self.del_btn.setProperty("class", "danger"); self.del_btn.clicked.connect(self._delete)
        btn_row.addWidget(self.edit_btn); btn_row.addWidget(self.del_btn); btn_row.addStretch()
        ll.addLayout(btn_row)
        splitter.addWidget(left)

        self._detail = QWidget(); self._detail.setObjectName("detailPanel")
        dl = QVBoxLayout(self._detail); dl.setContentsMargins(16,16,16,16)
        self._detail_title = QLabel(t('ui.expenses_widget.ausgabe_auswahlen_420faa03')); self._detail_title.setStyleSheet("font-size:16px;font-weight:bold;color:#1e2a38;")
        dl.addWidget(self._detail_title)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameStyle(QFrame.Shape.NoFrame)
        self._detail_body = QWidget(); self._detail_layout = QVBoxLayout(self._detail_body)
        scroll.setWidget(self._detail_body); dl.addWidget(scroll)
        splitter.addWidget(self._detail)
        splitter.setSizes([820, 320])
        root.addWidget(splitter)

    @staticmethod
    def _summary_card(value, label):
        w = QWidget(); w.setObjectName("summaryCard")
        vl = QVBoxLayout(w); vl.setContentsMargins(10,8,10,8)
        val = QLabel(value); val.setObjectName("summaryValue"); val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        txt = QLabel(label); txt.setObjectName("summaryLabel"); txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vl.addWidget(val); vl.addWidget(txt)
        return w

    def refresh(self):
        session = get_session()
        try:
            expenses = session.query(Expense).order_by(Expense.purchase_date.desc().nullslast(), Expense.id.desc()).all()
            self.stack.setCurrentIndex(1 if not expenses else 0)
            self.table.setRowCount(len(expenses))
            totals_by_type_cur = defaultdict(float)
            grand_by_cur = defaultdict(float)

            for row, exp in enumerate(expenses):
                currency = exp.currency or "CHF"
                date_str = format_date(exp.purchase_date) if exp.purchase_date else "—"
                cat_str = _item_type_label(exp.item_type)
                obj = exp.linked_label if hasattr(exp, "linked_label") else self._linked_label(exp)
                desc = exp.description or ""
                vendor = getattr(exp, "vendor", None) or ""

                date_item = QTableWidgetItem(date_str); date_item.setData(Qt.ItemDataRole.UserRole, exp.id)
                self.table.setItem(row, 0, date_item)
                self.table.setItem(row, 1, QTableWidgetItem(cat_str))
                self.table.setItem(row, 2, QTableWidgetItem(obj))
                self.table.setItem(row, 3, QTableWidgetItem(desc))
                self.table.setItem(row, 4, QTableWidgetItem(vendor))
                self.table.setItem(row, 5, QTableWidgetItem(_money(exp.amount, currency)))
                self.table.setItem(row, 6, QTableWidgetItem(_money(exp.shipping, currency) if exp.shipping else ""))
                self.table.setItem(row, 7, QTableWidgetItem(_money(exp.customs, currency) if exp.customs else ""))
                total_item = QTableWidgetItem(_money(exp.total, currency)); total_item.setForeground(QColor("#1e2a38"))
                self.table.setItem(row, 8, total_item)

                grand_by_cur[currency] += exp.total
                totals_by_type_cur[(exp.item_type, currency)] += exp.total

            def fmt_cur_map(m: dict[str, float]) -> str:
                if not m: return "—"
                return " / ".join(_money(v, k) for k, v in sorted(m.items()))

            def type_map(item_type: str) -> dict[str, float]:
                d = defaultdict(float)
                for (t, cur), val in totals_by_type_cur.items():
                    if t == item_type: d[cur] += val
                return dict(d)

            rest = defaultdict(float)
            for (t, cur), val in totals_by_type_cur.items():
                if t in {"accessory", "shipping", "customs", "other"}: rest[cur] += val

            self._set_card(self._total_lbl, fmt_cur_map(dict(grand_by_cur)))
            self._set_card(self._pens_lbl, fmt_cur_map(type_map("pen")))
            self._set_card(self._inks_lbl, fmt_cur_map(type_map("ink")))
            self._set_card(self._nibs_lbl, fmt_cur_map(type_map("nib")))
            self._set_card(self._paper_lbl, fmt_cur_map(type_map("paper")))
            self._set_card(self._service_lbl, fmt_cur_map(type_map("service")))
            self._set_card(self._other_lbl, fmt_cur_map(dict(rest)))
            self._filter()
        finally:
            session.close()

    @staticmethod
    def _set_card(card, txt):
        card.layout().itemAt(0).widget().setText(txt)

    @staticmethod
    def _linked_label(exp: Expense) -> str:
        if exp.pen: return f"{exp.pen.brand} {exp.pen.model}"
        if exp.ink: return f"{exp.ink.brand} {exp.ink.name}"
        if getattr(exp, "nib", None): return f"{exp.nib.manufacturer or ''} {exp.nib.size or ''}".strip()
        if exp.paper: return f"{exp.paper.brand} {exp.paper.name}"
        return ""

    def _filter(self):
        text = self.search_edit.text().lower() if hasattr(self, "search_edit") else ""
        cat = self.category_filter.currentData() if hasattr(self, "category_filter") else ""
        cat_label = _item_type_label(cat) if cat else ""
        for r in range(self.table.rowCount()):
            row_text = " ".join(self.table.item(r, c).text().lower() for c in range(self.table.columnCount()) if self.table.item(r, c))
            cat_ok = not cat or (self.table.item(r,1) and self.table.item(r,1).text() == cat_label)
            text_ok = not text or text in row_text
            self.table.setRowHidden(r, not (cat_ok and text_ok))

    def _selected_id(self):
        row = self.table.currentRow()
        if row < 0: return None
        item = self.table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _on_select(self):
        exp_id = self._selected_id()
        self.edit_btn.setEnabled(exp_id is not None)
        self.del_btn.setEnabled(exp_id is not None)
        if exp_id: self._show_details(exp_id)

    def _clear_details(self):
        while self._detail_layout.count():
            i = self._detail_layout.takeAt(0)
            if i.widget(): i.widget().deleteLater()

    def _show_details(self, exp_id: int):
        session = get_session()
        try:
            exp = session.get(Expense, exp_id)
            if not exp: return
            self._clear_details()
            self._detail_title.setText(exp.description or self._linked_label(exp) or _item_type_label(exp.item_type) or t("expenses.add"))
            def row(label, val):
                w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(0,2,0,2)
                l = QLabel(f"<b>{label}</b>"); l.setStyleSheet("color:#64748b; min-width:120px;")
                v = QLabel(str(val) if val not in (None, "") else "—"); v.setWordWrap(True)
                h.addWidget(l); h.addWidget(v, 1); self._detail_layout.addWidget(w)
            row(t("ui.expenses_widget.kategorie_a2aa2e02"), _item_type_label(exp.item_type))
            row(t("ui.expenses_widget.objekt_f7951b6e"), self._linked_label(exp))
            row(t("ui.expenses_widget.handler_8b886ac0"), getattr(exp, "vendor", None))
            row(t("ui.expenses_widget.bestell_rechnungsnr_9c4e3fd2"), getattr(exp, "order_number", None))
            row(t("ui.expenses_widget.zahlungsart_b987e44c"), getattr(exp, "payment_method", None))
            row(t("ui.expenses_widget.datum_441afa63"), format_date(exp.purchase_date) if exp.purchase_date else None)
            row(t("ui.expenses_widget.garantie_bis_70e449ef"), format_date(exp.warranty_until) if getattr(exp, "warranty_until", None) else None)
            row(t("ui.expenses_widget.betrag_4d8517b4"), _money(exp.amount, exp.currency or "CHF"))
            row(t("ui.expenses_widget.versand_681fd4b2"), _money(exp.shipping, exp.currency or "CHF") if exp.shipping else None)
            row(t("ui.expenses_widget.zoll_532508a1"), _money(exp.customs, exp.currency or "CHF") if exp.customs else None)
            row(t("ui.expenses_widget.gesamt_edc5a63c"), _money(exp.total, exp.currency or "CHF"))
            if exp.notes:
                note = QLabel(exp.notes); note.setWordWrap(True); note.setStyleSheet("background:#f8fafc;border:1px solid #d5dce6;border-radius:6px;padding:8px;")
                self._detail_layout.addWidget(note)
            self._detail_layout.addStretch()
        finally:
            session.close()

    def _context_menu(self, pos):
        row = self.table.rowAt(pos.y())
        if row >= 0:
            self.table.selectRow(row); self._on_select()
        menu = QMenu(self)
        add = menu.addAction(t('ui.expenses_widget.neu_hinzufugen_7e875cd7'))
        edit = menu.addAction(t('ui.expenses_widget.bearbeiten_51643aed'))
        delete = menu.addAction(t('ui.expenses_widget.loschen_995b44de'))
        has = self._selected_id() is not None
        edit.setEnabled(has); delete.setEnabled(has)
        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if action == add: self._add()
        elif action == edit: self._edit()
        elif action == delete: self._delete()

    def _add(self):
        dlg = ExpenseDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            session = get_session()
            try:
                data = dlg.get_data()
                exp = Expense(**data)
                session.add(exp)
                session.flush()
                _sync_pen_values_from_expenses(session, data.get("pen_id"))
                session.commit(); sync_default_outbox_from_session(session); self.refresh()
                bus = AppEventBus.instance(); bus.expenses_changed.emit(); bus.pens_changed.emit()
            except Exception as e:
                session.rollback(); QMessageBox.critical(self, t('ui.expenses_widget.fehler_41b1f911'), str(e))
            finally:
                session.close()

    def _edit(self):
        exp_id = self._selected_id()
        if not exp_id: return
        session = get_session()
        try:
            exp = session.get(Expense, exp_id)
            if not exp: return
            dlg = ExpenseDialog(self, exp)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                old_pen_id = exp.pen_id
                data = dlg.get_data()
                for k, v in data.items(): setattr(exp, k, v)
                session.flush()
                _sync_pen_values_from_expenses(session, old_pen_id)
                _sync_pen_values_from_expenses(session, data.get("pen_id"))
                session.commit(); sync_default_outbox_from_session(session); self.refresh(); self._show_details(exp_id)
                bus = AppEventBus.instance(); bus.expenses_changed.emit(); bus.pens_changed.emit()
        except Exception as e:
            session.rollback(); QMessageBox.critical(self, t('ui.expenses_widget.fehler_41b1f911'), str(e))
        finally:
            session.close()

    def _delete(self):
        exp_id = self._selected_id()
        if not exp_id: return
        session = get_session()
        try:
            exp = session.get(Expense, exp_id)
            if not exp: return
            if QMessageBox.question(self, t('ui.expenses_widget.loschen_be1b230e'), t('ui.expenses_widget.ausgabe_wirklich_loschen_29582e89'), QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                old_pen_id = exp.pen_id
                session.delete(exp)
                session.flush()
                _sync_pen_values_from_expenses(session, old_pen_id)
                session.commit(); sync_default_outbox_from_session(session); self.refresh(); self._clear_details(); self._detail_title.setText(t('ui.expenses_widget.ausgabe_auswahlen_420faa03'))
                bus = AppEventBus.instance(); bus.expenses_changed.emit(); bus.pens_changed.emit()
        finally:
            session.close()


class ExpenseDialog(QDialog):
    def __init__(self, parent=None, expense: Expense | None = None):
        super().__init__(parent)
        self.expense = expense
        self.setWindowTitle(t("expenses.edit_title") if expense else t("expenses.add_title"))
        self.setMinimumWidth(scale_px(560))
        self._setup_ui()
        self._load_options()
        if expense: self._fill(expense)

    def _setup_ui(self):
        root = QVBoxLayout(self)
        grp = QGroupBox(t('ui.expenses_widget.ausgabe_fc69fcf1')); fl = QFormLayout(grp)

        self.type_combo = QComboBox()
        for val, lbl in _item_types(): self.type_combo.addItem(lbl, val)
        self.type_combo.currentIndexChanged.connect(self._reload_linked)

        self.link_combo = QComboBox(); self.link_combo.addItem(t('ui.expenses_widget.nicht_verknupfen_45c850c8'), None)
        self.desc_edit = QLineEdit(); self.desc_edit.setPlaceholderText(t('ui.expenses_widget.z_b_pelikan_m800_service_lamy_2000_tintenbestell_d5e32dd6'))
        self.vendor_edit = QLineEdit(); self.vendor_edit.setPlaceholderText(t('ui.expenses_widget.z_b_landolt_stilo_e_stile_galaxus_bbd279d6'))
        self.order_edit = QLineEdit(); self.order_edit.setPlaceholderText(t('ui.expenses_widget.bestellnr_rechnung_tracking_cb8960b2'))
        self.payment_combo = QComboBox(); self.payment_combo.addItems(_payment_methods())
        self.currency_combo = QComboBox(); self.currency_combo.addItems(CURRENCIES)
        self.date_edit = QDateEdit(QDate.currentDate()); self.date_edit.setCalendarPopup(True); self.date_edit.setDisplayFormat(LocaleService.instance().qt_date_format)
        self.amt_spin = QDoubleSpinBox(); self.amt_spin.setRange(0, 999999); self.amt_spin.setSuffix(t('ui.expenses_widget.betrag_f6f93924')); self.amt_spin.setDecimals(2)
        self.ship_spin = QDoubleSpinBox(); self.ship_spin.setRange(0, 99999); self.ship_spin.setSuffix(t('ui.expenses_widget.versand_ec453a72')); self.ship_spin.setDecimals(2)
        self.cust_spin = QDoubleSpinBox(); self.cust_spin.setRange(0, 99999); self.cust_spin.setSuffix(t('ui.expenses_widget.zoll_a2b67bcc')); self.cust_spin.setDecimals(2)
        self.has_warranty = QCheckBox(t('ui.expenses_widget.garantie_servicefrist_erfassen_cf290f4e'))
        self.warranty_edit = QDateEdit(QDate.currentDate().addYears(2)); self.warranty_edit.setCalendarPopup(True); self.warranty_edit.setDisplayFormat(LocaleService.instance().qt_date_format); self.warranty_edit.setEnabled(False)
        self.has_warranty.toggled.connect(self.warranty_edit.setEnabled)
        self.notes_edit = QTextEdit(); self.notes_edit.setMaximumHeight(90)

        fl.addRow(t('ui.expenses_widget.kategorie_a2aa2e02'), self.type_combo)
        fl.addRow(t('ui.expenses_widget.verknupft_mit_d800f620'), self.link_combo)
        fl.addRow(t('ui.expenses_widget.beschreibung_3c599e40'), self.desc_edit)
        fl.addRow(t('ui.expenses_widget.handler_anbieter_0f773fbc'), self.vendor_edit)
        fl.addRow(t('ui.expenses_widget.bestell_rechnungsnr_9c4e3fd2'), self.order_edit)
        fl.addRow(t('ui.expenses_widget.zahlungsart_b987e44c'), self.payment_combo)
        fl.addRow(t('ui.expenses_widget.wahrung_362832d5'), self.currency_combo)
        fl.addRow(t('ui.expenses_widget.datum_441afa63'), self.date_edit)
        fl.addRow(t('ui.expenses_widget.betrag_4d8517b4'), self.amt_spin)
        fl.addRow(t('ui.expenses_widget.versand_681fd4b2'), self.ship_spin)
        fl.addRow(t('ui.expenses_widget.zoll_532508a1'), self.cust_spin)
        fl.addRow(self.has_warranty, self.warranty_edit)
        fl.addRow(t('ui.expenses_widget.notizen_b13c7c4a'), self.notes_edit)
        root.addWidget(grp)

        br = QHBoxLayout(); br.addStretch()
        cancel = QPushButton(t('ui.expenses_widget.abbrechen_2f5fb27f')); cancel.setProperty("class", "secondary"); cancel.clicked.connect(self.reject)
        save = QPushButton(t('ui.expenses_widget.speichern_88bf668a')); save.setProperty("class", "success"); save.clicked.connect(self.accept)
        br.addWidget(cancel); br.addWidget(save); root.addLayout(br)

    def _load_options(self):
        self._reload_linked()

    def _reload_linked(self):
        cur_type = self.type_combo.currentData()
        current = self.link_combo.currentData() if hasattr(self, "link_combo") else None
        self.link_combo.blockSignals(True); self.link_combo.clear(); self.link_combo.addItem(t('ui.expenses_widget.nicht_verknupfen_45c850c8'), None)
        session = get_session()
        try:
            if cur_type in ("pen", "service"):
                for p in session.query(Pen).order_by(Pen.brand, Pen.model).all():
                    self.link_combo.addItem(f"{p.brand} {p.model}", ("pen", p.id))
            elif cur_type == "ink":
                for i in session.query(Ink).order_by(Ink.brand, Ink.name).all():
                    self.link_combo.addItem(f"{i.brand} {i.name}", ("ink", i.id))
            elif cur_type == "nib":
                for n in session.query(Nib).order_by(Nib.manufacturer, Nib.size).all():
                    self.link_combo.addItem(f"{n.manufacturer or t('expenses.nib_fallback')} {n.size or ''} {n.material or ''}".strip(), ("nib", n.id))
            elif cur_type == "paper":
                for p in session.query(Paper).order_by(Paper.brand, Paper.name).all():
                    self.link_combo.addItem(f"{p.brand} {p.name}", ("paper", p.id))
        finally:
            session.close(); self.link_combo.blockSignals(False)
        if current:
            for idx in range(self.link_combo.count()):
                if self.link_combo.itemData(idx) == current:
                    self.link_combo.setCurrentIndex(idx); break

    def _fill(self, exp: Expense):
        for idx in range(self.type_combo.count()):
            if self.type_combo.itemData(idx) == exp.item_type:
                self.type_combo.setCurrentIndex(idx); break
        self._reload_linked()
        linked = None
        if exp.pen_id: linked = ("pen", exp.pen_id)
        elif exp.ink_id: linked = ("ink", exp.ink_id)
        elif getattr(exp, "nib_id", None): linked = ("nib", exp.nib_id)
        elif exp.paper_id: linked = ("paper", exp.paper_id)
        if linked:
            for idx in range(self.link_combo.count()):
                if self.link_combo.itemData(idx) == linked:
                    self.link_combo.setCurrentIndex(idx); break
        self.desc_edit.setText(exp.description or "")
        self.vendor_edit.setText(getattr(exp, "vendor", None) or "")
        self.order_edit.setText(getattr(exp, "order_number", None) or "")
        if getattr(exp, "payment_method", None):
            i = self.payment_combo.findText(exp.payment_method)
            if i >= 0: self.payment_combo.setCurrentIndex(i)
        i = self.currency_combo.findText(exp.currency or "CHF")
        if i >= 0: self.currency_combo.setCurrentIndex(i)
        if exp.purchase_date: self.date_edit.setDate(QDate(exp.purchase_date.year, exp.purchase_date.month, exp.purchase_date.day))
        self.amt_spin.setValue(exp.amount or 0.0); self.ship_spin.setValue(exp.shipping or 0.0); self.cust_spin.setValue(exp.customs or 0.0)
        if getattr(exp, "warranty_until", None):
            self.has_warranty.setChecked(True)
            self.warranty_edit.setDate(QDate(exp.warranty_until.year, exp.warranty_until.month, exp.warranty_until.day))
        self.notes_edit.setPlainText(exp.notes or "")

    def get_data(self) -> dict:
        d = self.date_edit.date()
        wd = self.warranty_edit.date()
        link = self.link_combo.currentData()
        data = {
            "item_type": self.type_combo.currentData(),
            "description": self.desc_edit.text().strip() or None,
            "vendor": self.vendor_edit.text().strip() or None,
            "order_number": self.order_edit.text().strip() or None,
            "payment_method": self.payment_combo.currentText() or None,
            "currency": self.currency_combo.currentText() or "CHF",
            "purchase_date": datetime(d.year(), d.month(), d.day()),
            "amount": self.amt_spin.value(),
            "shipping": self.ship_spin.value(),
            "customs": self.cust_spin.value(),
            "warranty_until": datetime(wd.year(), wd.month(), wd.day()) if self.has_warranty.isChecked() else None,
            "notes": self.notes_edit.toPlainText().strip() or None,
            "pen_id": None, "ink_id": None, "nib_id": None, "paper_id": None,
        }
        if link:
            kind, obj_id = link
            data[f"{kind}_id"] = obj_id
        return data
