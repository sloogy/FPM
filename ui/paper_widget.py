"""
Papierverwaltung – CRUD für Notizbücher und loses Papier.
"""
from datetime import datetime
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QDialog, QFormLayout, QSpinBox, QDateEdit,
    QTextEdit, QCheckBox, QGroupBox, QMessageBox, QComboBox,
    QStackedWidget, QMenu,
)
from PySide6.QtCore import Qt, QDate
from ui.locale_widgets import (
    LocalizedDoubleSpinBox as QDoubleSpinBox,
    bind_currency_combo,
    current_currency,
    populate_currency_combo,
    set_combo_currency,
)
from ui.ui_scale import scale_px
from database.db import get_session
from database.models import Paper, Expense
from i18n.translator import LocaleService, t
from ui.common import EmptyStateWidget
from logic.event_bus import AppEventBus
from logic.budget_export_service import sync_default_outbox_from_session
from ui.theme import BTN_MUTED, BTN_PRIMARY, BTN_SUCCESS

PAPER_TYPE_KEYS = ["notebook", "loose", "pad", "other"]

def _paper_types():
    return [(key, t(f"paper.types.{key}")) for key in PAPER_TYPE_KEYS]

def _paper_type_label(key: str | None) -> str:
    return dict(_paper_types()).get(key, key or "—")
SURFACE_OPTS = ["Glatt","Medium","Rau","Satiniert","Sonstige"]


def _sync_paper_expense(session, paper: Paper) -> None:
    """Papier-Kaufpreis als Ausgabeneintrag führen (genau 1 automatischer Eintrag pro Papier)."""
    auto_tag = f"AUTO-PAPER-PURCHASE:{paper.id}"
    exp = (
        session.query(Expense)
        .filter(Expense.paper_id == paper.id, Expense.notes == auto_tag, Expense.item_type == "paper")
        .first()
    )
    price = paper.purchase_price or 0.0
    if price <= 0:
        if exp:
            session.delete(exp)
        return
    if not exp:
        exp = Expense(
            item_type="paper", paper_id=paper.id,
            shipping=0.0, customs=0.0,
            currency=getattr(paper, "purchase_currency", None) or LocaleService.instance().currency,
            notes=auto_tag,
        )
        session.add(exp)
    exp.amount        = price
    exp.currency      = getattr(paper, "purchase_currency", None) or LocaleService.instance().currency
    exp.purchase_date = paper.purchase_date
    exp.description   = t("paper.purchase_description", brand=paper.brand, name=paper.name)


class PaperWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._setup_ui()
        AppEventBus.instance().papers_changed.connect(self.refresh)
        self.refresh()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24,24,24,24)
        root.setSpacing(16)

        hdr = QHBoxLayout()
        title = QLabel(t('ui.paper_widget.papierverwaltung_ec8f9d12'))
        title.setObjectName("page_title")
        hdr.addWidget(title); hdr.addStretch()

        self.search_edit = QLineEdit(); self.search_edit.setPlaceholderText(t('ui.paper_widget.suchen_b113da0c'))
        self.search_edit.setMinimumWidth(scale_px(220)); self.search_edit.textChanged.connect(self._filter)
        hdr.addWidget(self.search_edit)

        add_btn = QPushButton(t('ui.paper_widget.papier_hinzufugen_986b4afe'))
        add_btn.setStyleSheet(BTN_PRIMARY)
        add_btn.clicked.connect(self._add)
        hdr.addWidget(add_btn)
        root.addLayout(hdr)

        self.stack = QStackedWidget()

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            [t('ui.paper_widget.marke_96b8857e'),t('ui.paper_widget.name_ce7b74e7'),t('ui.paper_widget.typ_a368f8ec'),t('ui.paper_widget.g_m2_81d6c5c0'),t('ui.paper_widget.oberflache_b4c51b92'),t('ui.paper_widget.feathering_d65f9091'),t('ui.paper_widget.edc_dfdf528d')]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.clicked.connect(self._on_select)
        self.table.doubleClicked.connect(self._edit)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)

        self._empty_state = EmptyStateWidget(
            icon="📓",
            title=t("paper.empty_title"),
            subtitle=t("paper.empty_subtitle"),
            action_label=t("paper.add"),
            action_slot=self._add,
        )
        self.stack.addWidget(self.table)        # index 0
        self.stack.addWidget(self._empty_state) # index 1
        root.addWidget(self.stack)

        btn_row = QHBoxLayout()
        self.edit_btn = self._btn("✏  " + t("common.edit"),"#f39c12",self._edit,False)
        self.del_btn  = self._btn("🗑  " + t("common.delete"),  "#e74c3c",self._delete,False)
        btn_row.addWidget(self.edit_btn); btn_row.addWidget(self.del_btn); btn_row.addStretch()
        root.addLayout(btn_row)

    @staticmethod
    def _btn(t,c,s,e=True):
        b=QPushButton(t); b.setEnabled(e)
        b.setStyleSheet(f"background:{c};color:white;border:none;padding:6px 12px;border-radius:5px;")
        b.clicked.connect(s); return b

    def refresh(self):
        session = get_session()
        try:
            papers = session.query(Paper).all()
            if not papers:
                self.stack.setCurrentIndex(1)  # EmptyStateWidget
                return
            self.stack.setCurrentIndex(0)      # Tabelle
            self.table.setRowCount(len(papers))
            pt_dict = dict(_paper_types())
            for row, p in enumerate(papers):
                m = QTableWidgetItem(p.brand); m.setData(Qt.ItemDataRole.UserRole, p.id)
                self.table.setItem(row,0,m)
                self.table.setItem(row,1,QTableWidgetItem(p.name))
                self.table.setItem(row,2,QTableWidgetItem(pt_dict.get(p.paper_type,p.paper_type)))
                self.table.setItem(row,3,QTableWidgetItem(str(p.weight_gsm) if p.weight_gsm else ""))
                self.table.setItem(row,4,QTableWidgetItem(p.surface or ""))
                self.table.setItem(row,5,QTableWidgetItem(f"{p.feathering_level}/5"))
                self.table.setItem(row,6,QTableWidgetItem("✓" if p.is_edc else ""))
        finally:
            session.close()

    def _filter(self,text):
        text=text.lower()
        for r in range(self.table.rowCount()):
            self.table.setRowHidden(r, not any(
                self.table.item(r,c) and text in self.table.item(r,c).text().lower()
                for c in range(self.table.columnCount())))

    def _selected_id(self):
        row=self.table.currentRow()
        if row<0: return None
        item=self.table.item(row,0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _on_select(self):
        pid=self._selected_id()
        for b in (self.edit_btn,self.del_btn): b.setEnabled(pid is not None)

    def _context_menu(self, pos):
        row = self.table.rowAt(pos.y())
        if row >= 0:
            self.table.selectRow(row)
            if hasattr(self, "_on_select"):
                self._on_select()
        menu = QMenu(self)
        add = menu.addAction(t('ui.paper_widget.neu_hinzufugen_a0c280c8'))
        edit = menu.addAction(t('ui.paper_widget.bearbeiten_95190570')) if hasattr(self, "_edit") else None
        delete = menu.addAction(t('ui.paper_widget.loschen_1c0ea5db')) if hasattr(self, "_delete") else None
        has_selection = self._selected_id() is not None if hasattr(self, "_selected_id") else row >= 0
        if edit: edit.setEnabled(has_selection)
        if delete: delete.setEnabled(has_selection)
        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if action == add: self._add()
        elif edit and action == edit: self._edit()
        elif delete and action == delete: self._delete()

    def _add(self):
        dlg=PaperDialog(self)
        if dlg.exec()==QDialog.DialogCode.Accepted:
            session=get_session()
            try:
                paper = Paper(**dlg.get_data())
                session.add(paper)
                session.flush()
                _sync_paper_expense(session, paper)
                session.commit()
                sync_default_outbox_from_session(session)
                AppEventBus.instance().papers_changed.emit()
                AppEventBus.instance().expenses_changed.emit()
                self.refresh()
            except Exception as e: QMessageBox.critical(self,t('ui.paper_widget.fehler_6f7add66'),str(e))
            finally: session.close()

    def _edit(self):
        pid=self._selected_id()
        if not pid: return
        session=get_session()
        try:
            p=session.get(Paper,pid)
            if not p: return
            dlg=PaperDialog(self,p)
            if dlg.exec()==QDialog.DialogCode.Accepted:
                for k,v in dlg.get_data().items(): setattr(p,k,v)
                _sync_paper_expense(session, p)
                session.commit()
                sync_default_outbox_from_session(session)
                AppEventBus.instance().papers_changed.emit()
                AppEventBus.instance().expenses_changed.emit()
                self.refresh()
        finally: session.close()

    def _delete(self):
        pid=self._selected_id()
        if not pid: return
        session=get_session()
        try:
            p=session.get(Paper,pid)
            if not p: return
            if QMessageBox.question(self,t('ui.paper_widget.loschen_c0857326'),t('ui.paper_widget.confirm_delete_paper', paper=f"{p.brand} {p.name}"),
                QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:
                session.delete(p); session.commit()
                AppEventBus.instance().papers_changed.emit()
                self.refresh()
        finally: session.close()


class PaperDialog(QDialog):
    def __init__(self, parent=None, paper: Optional[Paper]=None):
        super().__init__(parent)
        self.paper=paper
        self.setWindowTitle(t("paper.edit_title") if paper else t("paper.add_title"))
        self.setMinimumWidth(scale_px(500))
        self._setup_ui()
        if paper: self._load()

    def _setup_ui(self):
        root=QVBoxLayout(self)
        g1=QGroupBox(t('ui.paper_widget.grundinformationen_e8653b41')); f1=QFormLayout(g1)
        self.brand_edit=QLineEdit(); self.brand_edit.setPlaceholderText(t('ui.paper_widget.z_b_rhodia_leuchtturm_clairefontaine_5948f8bf'))
        self.name_edit =QLineEdit(); self.name_edit.setPlaceholderText(t('ui.paper_widget.z_b_no_19_80g_optik_paper_52fad86a'))
        self.type_combo=QComboBox()
        for val,lbl in _paper_types(): self.type_combo.addItem(lbl,val)
        self.weight_spin=QSpinBox(); self.weight_spin.setRange(0,300); self.weight_spin.setSuffix(t('ui.paper_widget.g_m2_9f6c2ca1'))
        self.surface_edit=QLineEdit(); self.surface_edit.setPlaceholderText(t('ui.paper_widget.glatt_medium_rau_7a278cbe'))
        f1.addRow(t('ui.paper_widget.marke_8ea75961'),     self.brand_edit)
        f1.addRow(t('ui.paper_widget.name_88897ba4'),      self.name_edit)
        f1.addRow(t('ui.paper_widget.typ_a368f8ec'),         self.type_combo)
        f1.addRow(t('ui.paper_widget.gewicht_2d1305bb'),     self.weight_spin)
        f1.addRow(t('ui.paper_widget.oberflache_b4c51b92'),  self.surface_edit)
        root.addWidget(g1)

        g2=QGroupBox(t('ui.paper_widget.eigenschaften_0eb39d51')); f2=QFormLayout(g2)
        self.feat_spin  =QSpinBox(); self.feat_spin.setRange(1,5); self.feat_spin.setSuffix(t('ui.paper_widget.1_kein_5_stark_68ca4a9f'))
        self.bleed_spin =QSpinBox(); self.bleed_spin.setRange(1,5); self.bleed_spin.setSuffix(t('ui.paper_widget.1_kein_5_stark_68ca4a9f'))
        self.shading_cb =QCheckBox(t('ui.paper_widget.shading_geeignet_982a4adb')); self.shading_cb.setChecked(True)
        self.sheen_cb   =QCheckBox(t('ui.paper_widget.sheen_geeignet_ff4c2553'))
        self.edc_cb     =QCheckBox(t('ui.paper_widget.edc_notizbuch_taglich_im_einsatz_cafd60b7'))
        f2.addRow(t('ui.paper_widget.feathering_d65f9091'),     self.feat_spin)
        f2.addRow(t('ui.paper_widget.durchschlag_59dea906'),    self.bleed_spin)
        f2.addRow("",               self.shading_cb)
        f2.addRow("",               self.sheen_cb)
        f2.addRow("",               self.edc_cb)
        root.addWidget(g2)

        g3=QGroupBox(t('ui.paper_widget.kauf_seitenstand_770a5f22')); f3=QFormLayout(g3)
        self.date_edit  =QDateEdit(QDate.currentDate()); self.date_edit.setCalendarPopup(True); self.date_edit.setDisplayFormat(LocaleService.instance().qt_date_format)
        default_cur = LocaleService.instance().currency
        self.price_spin =QDoubleSpinBox(); self.price_spin.setRange(0,999); self.price_spin.setDecimals(2)
        self.price_currency_combo = QComboBox(); populate_currency_combo(self.price_currency_combo, default_cur); bind_currency_combo(self.price_currency_combo, self.price_spin)
        self.pages_spin =QSpinBox(); self.pages_spin.setRange(0,9999); self.pages_spin.setSuffix(t('ui.paper_widget.seiten_gesamt_20d48e06'))
        self.used_spin  =QSpinBox(); self.used_spin.setRange(0,9999); self.used_spin.setSuffix(t('ui.paper_widget.seiten_verbraucht_c62fff3b'))
        self.notes_edit =QTextEdit(); self.notes_edit.setMaximumHeight(70)
        f3.addRow(t('ui.paper_widget.kaufdatum_20a44b17'),  self.date_edit)
        f3.addRow(t('ui.paper_widget.preis_7a77829b'),      self.price_spin)
        f3.addRow(t('ui.paper_widget.wahrung_7ae1bf40'),    self.price_currency_combo)
        f3.addRow(t('ui.paper_widget.seiten_872d4e38'),     self.pages_spin)
        f3.addRow(t('ui.paper_widget.verbraucht_c6a4a47b'), self.used_spin)
        f3.addRow(t('ui.paper_widget.notizen_e645d416'),    self.notes_edit)
        root.addWidget(g3)

        br=QHBoxLayout(); br.addStretch()
        cancel=QPushButton(t('ui.paper_widget.abbrechen_7baa411a')); cancel.setStyleSheet(BTN_MUTED); cancel.clicked.connect(self.reject)
        save=QPushButton(t('ui.paper_widget.speichern_8fa88b2c')); save.setStyleSheet(BTN_SUCCESS); save.clicked.connect(self._save)
        br.addWidget(cancel); br.addWidget(save); root.addLayout(br)

    def _load(self):
        p=self.paper
        self.brand_edit.setText(p.brand or ""); self.name_edit.setText(p.name or "")
        for i,(val,_) in enumerate(_paper_types()):
            if val==p.paper_type: self.type_combo.setCurrentIndex(i); break
        self.weight_spin.setValue(p.weight_gsm or 0)
        self.surface_edit.setText(p.surface or "")
        self.feat_spin.setValue(p.feathering_level); self.bleed_spin.setValue(p.bleedthrough_level)
        self.shading_cb.setChecked(p.shading_suitable); self.sheen_cb.setChecked(p.sheen_suitable)
        self.edc_cb.setChecked(p.is_edc)
        if p.purchase_date:
            d=p.purchase_date; self.date_edit.setDate(QDate(d.year,d.month,d.day))
        self.price_spin.setValue(p.purchase_price or 0)
        set_combo_currency(self.price_currency_combo, getattr(p, "purchase_currency", None))
        self.pages_spin.setValue(p.pages_total or 0); self.used_spin.setValue(p.pages_used or 0)
        self.notes_edit.setPlainText(p.notes or "")

    def _save(self):
        if not self.brand_edit.text().strip():
            QMessageBox.warning(self,t('ui.paper_widget.pflichtfeld_1a3eeef3'),t('ui.paper_widget.bitte_marke_eingeben_d6a83c98')); return
        if not self.name_edit.text().strip():
            QMessageBox.warning(self,t('ui.paper_widget.pflichtfeld_1a3eeef3'),t('ui.paper_widget.bitte_name_eingeben_9b0d109a')); return
        self.accept()

    def get_data(self)->dict:
        d=self.date_edit.date()
        return {
            "brand":self.brand_edit.text().strip(), "name":self.name_edit.text().strip(),
            "paper_type":self.type_combo.currentData(),
            "weight_gsm":self.weight_spin.value() or None,
            "surface":self.surface_edit.text().strip() or None,
            "feathering_level":self.feat_spin.value(), "bleedthrough_level":self.bleed_spin.value(),
            "shading_suitable":self.shading_cb.isChecked(), "sheen_suitable":self.sheen_cb.isChecked(),
            "is_edc":self.edc_cb.isChecked(),
            "purchase_date":datetime(d.year(),d.month(),d.day()),
            "purchase_price":self.price_spin.value() or None,
            "purchase_currency": current_currency(self.price_currency_combo),
            "pages_total":self.pages_spin.value() or None,
            "pages_used":self.used_spin.value(),
            "notes":self.notes_edit.toPlainText().strip() or None,
        }
