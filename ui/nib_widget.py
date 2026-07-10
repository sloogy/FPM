"""
Federverwaltung – CRUD für Federn/Nibs.
"""
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QDialog, QFormLayout, QSpinBox, QTextEdit, QCheckBox,
    QGroupBox, QScrollArea, QMessageBox, QFrame, QMenu,
    QStackedWidget, QComboBox,
)
from PySide6.QtCore import Qt
from ui.ui_scale import scale_px
from database.db import get_session
from database.models import Nib, NibFormat
from ui.common import EmptyStateWidget
from logic.event_bus import AppEventBus
from i18n.translator import t
from ui.theme import BTN_MUTED, BTN_PRIMARY, BTN_SUCCESS

NIB_SIZES = ["EF", "F", "M", "B", "BB", "Stub 1.1", "Stub 1.5", "Stub 1.9", "Flex", t("paper.types.other")]


class NibWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._setup_ui()
        AppEventBus.instance().nibs_changed.connect(self.refresh)
        self.refresh()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        hdr = QHBoxLayout()
        title = QLabel(t('ui.nib_widget.federverwaltung_f3778ea6'))
        title.setObjectName("page_title")
        hdr.addWidget(title)
        hdr.addStretch()

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(t('ui.nib_widget.suchen_63a67d04'))
        self.search_edit.setMinimumWidth(scale_px(220))
        self.search_edit.textChanged.connect(self._filter)
        hdr.addWidget(self.search_edit)

        add_btn = QPushButton(t('ui.nib_widget.feder_hinzufugen_f3956c58'))
        add_btn.setStyleSheet(BTN_PRIMARY)
        add_btn.clicked.connect(self._add)
        hdr.addWidget(add_btn)
        root.addLayout(hdr)

        self.stack = QStackedWidget()

        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels(
            [t('ui.nib_widget.marke_adec8876'), t('ui.nib_widget.feinheit_98dcd30d'), t('ui.nib_widget.baugroe_2a256087'), t('ui.nib_widget.material_9273c293'), t('ui.nib_widget.proprietar_6db02f77'), t('ui.nib_widget.schliff_e34c2d59'), t('ui.nib_widget.nibmeister_7e6431bb'), t('ui.nib_widget.ruckmeldung_194c5054'), t('ui.nib_widget.flexibel_d2aeb8bf'), t('ui.nib_widget.bezug_a758bb88'), t('ui.nib_widget.steifigkeit_0c308bb9')]
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
            icon="🖊️",
            title=t("ui.nib_widget.empty_title"),
            subtitle=t("ui.nib_widget.empty_subtitle"),
            action_label=t("ui.nib_widget.empty_action"),
            action_slot=self._add,
        )

        self.stack.addWidget(self.table)       # index 0
        self.stack.addWidget(self._empty_state) # index 1
        root.addWidget(self.stack)

        btn_row = QHBoxLayout()
        self.edit_btn = self._mk_btn("✏  " + t("common.edit"), "#f39c12", self._edit, False)
        self.del_btn  = self._mk_btn("🗑  " + t("common.delete"),   "#e74c3c", self._delete, False)
        btn_row.addWidget(self.edit_btn)
        btn_row.addWidget(self.del_btn)
        btn_row.addStretch()
        root.addLayout(btn_row)

    @staticmethod
    def _mk_btn(text, color, slot, enabled=True):
        b = QPushButton(text)
        b.setEnabled(enabled)
        b.setStyleSheet(f"background:{color};color:white;border:none;padding:6px 12px;border-radius:5px;")
        b.clicked.connect(slot)
        return b

    def refresh(self):
        session = get_session()
        try:
            nibs = session.query(Nib).all()
            if not nibs:
                self.stack.setCurrentIndex(1)   # EmptyStateWidget
                return
            self.stack.setCurrentIndex(0)       # Tabelle
            self.table.setRowCount(len(nibs))
            for row, nib in enumerate(nibs):
                m = QTableWidgetItem(nib.effective_manufacturer or "")
                m.setData(Qt.ItemDataRole.UserRole, nib.id)
                self.table.setItem(row, 0, m)
                self.table.setItem(row, 1, QTableWidgetItem(nib.size or ""))
                self.table.setItem(row, 2, QTableWidgetItem(nib.effective_physical_size or ""))
                self.table.setItem(row, 3, QTableWidgetItem(getattr(nib, "material", None) or ""))
                self.table.setItem(row, 4, QTableWidgetItem("✓" if nib.effective_is_proprietary else ""))
                self.table.setItem(row, 5, QTableWidgetItem(nib.grind or ""))
                self.table.setItem(row, 6, QTableWidgetItem(nib.nibmeister or ""))
                self.table.setItem(row, 7, QTableWidgetItem(f"{nib.feedback_level} / 5"))
                self.table.setItem(row, 8, QTableWidgetItem("✓" if nib.is_flexible else ""))
                self.table.setItem(row, 9, QTableWidgetItem(getattr(nib, "source", None) or ""))
                self.table.setItem(row, 10, QTableWidgetItem(f"{getattr(nib, 'stiffness_level', 4) or 4} / 5"))
        finally:
            session.close()

    def _filter(self, text):
        text = text.lower()
        for r in range(self.table.rowCount()):
            vis = any(
                self.table.item(r, c) and text in self.table.item(r, c).text().lower()
                for c in range(self.table.columnCount())
            )
            self.table.setRowHidden(r, not vis)

    def _selected_id(self):
        row = self.table.currentRow()
        if row < 0: return None
        item = self.table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _on_select(self):
        nib_id = self._selected_id()
        for b in (self.edit_btn, self.del_btn):
            b.setEnabled(nib_id is not None)

    def _context_menu(self, pos):
        row = self.table.rowAt(pos.y())
        if row >= 0:
            self.table.selectRow(row)
        menu = QMenu(self)
        add = menu.addAction(t('ui.nib_widget.feder_hinzufugen_f3956c58'))
        edit = menu.addAction(t('ui.nib_widget.bearbeiten_d7acb685'))
        delete = menu.addAction(t('ui.nib_widget.loschen_96812e50'))
        has_selection = self._selected_id() is not None
        edit.setEnabled(has_selection); delete.setEnabled(has_selection)
        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if action == add: self._add()
        elif action == edit: self._edit()
        elif action == delete: self._delete()

    def _add(self):
        dlg = NibDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            session = get_session()
            try:
                data = dlg.get_data()
                data["format_id"] = dlg.resolve_format(session)
                session.add(Nib(**data))
                session.commit()
                AppEventBus.instance().nibs_changed.emit()
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, t('ui.nib_widget.fehler_d9532c6b'), str(e))
            finally:
                session.close()

    def _edit(self):
        nib_id = self._selected_id()
        if not nib_id: return
        session = get_session()
        try:
            nib = session.get(Nib, nib_id)
            if not nib: return
            dlg = NibDialog(self, nib)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                data = dlg.get_data()
                data["format_id"] = dlg.resolve_format(session)
                for k, v in data.items():
                    setattr(nib, k, v)
                session.commit()
                AppEventBus.instance().nibs_changed.emit()
                self.refresh()
        finally:
            session.close()

    def _delete(self):
        nib_id = self._selected_id()
        if not nib_id: return
        session = get_session()
        try:
            nib = session.get(Nib, nib_id)
            if not nib: return
            active_setups = [setup for setup in (getattr(nib, "setups", []) or []) if setup.is_active and setup.removed_date is None]
            if nib.pens or active_setups:
                QMessageBox.warning(self, t('ui.nib_widget.nicht_moglich_fa9c7617'),
                    t('ui.nib_widget.diese_feder_ist_einem_fuller_oder_einem_aktiven__8c641d5b'))
                return
            if QMessageBox.question(
                self, t('ui.nib_widget.loschen_b0605854'), t('ui.nib_widget.confirm_delete_nib', label=nib.display_label),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            ) == QMessageBox.StandardButton.Yes:
                session.delete(nib)
                session.commit()
                AppEventBus.instance().nibs_changed.emit()
                self.refresh()
        finally:
            session.close()


class NibDialog(QDialog):
    """Dialog für eine Feder-Einheit (Exemplar).

    Zwei klar getrennte Bereiche:
    - Format & Kompatibilität (NibFormat): bestimmt, in welche Füller die Feder passt.
      Wird über einen Picker geteilt – mehrere Exemplare teilen sich dasselbe Format.
    - Exemplar / Schreibgefühl: individuelle Felder dieser konkreten Feder
      (Source/Tuner, Feed, Steifigkeit, Smoothness, Notizen).

    Duplikat-Logik:
    - Formate werden dedupliziert (Marke + Baugröße + proprietär).
    - Exemplare NICHT – zwei Bock #6 vom selben Tuner sind eigene Federn.
    """
    def __init__(self, parent=None, nib: Optional[Nib] = None):
        super().__init__(parent)
        self.nib = nib
        self.setWindowTitle(t("nib.edit_title") if nib else t("nib.add_title"))
        self.setMinimumWidth(scale_px(560))
        self.setMinimumHeight(scale_px(640))
        self._setup_ui()
        self._reload_formats(select_id=getattr(nib, "format_id", None) if nib else None)
        if nib: self._load()
        self._on_format_combo_changed(0)

    def _setup_ui(self):
        root = QVBoxLayout(self)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        body = QWidget(); body_l = QVBoxLayout(body); body_l.setSpacing(14)

        # ── Format / Kompatibilität ──────────────────────────────────
        grp_fmt = QGroupBox(t('ui.nib_widget.format_kompatibilitat_geteilt_zwischen_exemplare_1879216f'))
        fl_fmt = QFormLayout(grp_fmt); fl_fmt.setVerticalSpacing(10)
        self.format_combo = QComboBox()
        self.format_combo.currentIndexChanged.connect(self._on_format_combo_changed)
        fl_fmt.addRow(t('ui.nib_widget.vorhandenes_format_9230bc06'), self.format_combo)
        self.fmt_mfr_edit  = QLineEdit(); self.fmt_mfr_edit.setPlaceholderText(t('ui.nib_widget.z_b_bock_jowo_schmidt_pilot_7f325cc5'))
        self.fmt_phys_edit = QLineEdit(); self.fmt_phys_edit.setPlaceholderText(t('ui.nib_widget.z_b_5_6_8_pilot_10_lamy_2000_29049c4a'))
        self.fmt_prop_cb   = QCheckBox(t('ui.nib_widget.proprietares_format_nicht_standard_kompatibel_1bda1c74'))
        self.fmt_compat_edit = QTextEdit(); self.fmt_compat_edit.setMaximumHeight(60)
        self.fmt_compat_edit.setPlaceholderText(t('ui.nib_widget.fuller_die_dieses_format_aufnehmen_z_b_jinhao_x7_3054a1f1'))
        self.fmt_notes_edit  = QTextEdit(); self.fmt_notes_edit.setMaximumHeight(50)
        self.fmt_notes_edit.setPlaceholderText(t('ui.nib_widget.hinweise_zum_format_de090063'))
        fl_fmt.addRow(t('ui.nib_widget.marke_hersteller_80d63a7b'), self.fmt_mfr_edit)
        fl_fmt.addRow(t('ui.nib_widget.baugroe_2a256087'),           self.fmt_phys_edit)
        fl_fmt.addRow("",                   self.fmt_prop_cb)
        fl_fmt.addRow(t('ui.nib_widget.passt_in_fuller_2f07c07e'),  self.fmt_compat_edit)
        fl_fmt.addRow(t('ui.nib_widget.format_notiz_3a619ffd'),       self.fmt_notes_edit)
        self._fmt_inputs = [self.fmt_mfr_edit, self.fmt_phys_edit, self.fmt_prop_cb,
                            self.fmt_compat_edit, self.fmt_notes_edit]
        body_l.addWidget(grp_fmt)

        # ── Exemplar / Schreibgefühl ─────────────────────────────────
        grp_unit = QGroupBox(t('ui.nib_widget.exemplar_diese_konkrete_feder_schreibgefuhl_68e31f4c'))
        fl = QFormLayout(grp_unit); fl.setVerticalSpacing(10)
        self.label_edit  = QLineEdit(); self.label_edit.setPlaceholderText(t('ui.nib_widget.spitzname_z_b_gravitas_tuned_bock_6_ef_03013a18'))
        self.size_edit   = QLineEdit(); self.size_edit.setPlaceholderText(t('ui.nib_widget.z_b_ef_f_m_b_stub_1_1_948c925e'))
        self.material_edit = QLineEdit(); self.material_edit.setPlaceholderText(t('ui.nib_widget.z_b_stahl_14k_gold_18k_gold_titan_cccf50a6'))
        self.grind_edit  = QLineEdit(); self.grind_edit.setPlaceholderText(t('ui.nib_widget.z_b_italic_cursive_italic_ci_8573bf32'))
        self.source_edit = QLineEdit(); self.source_edit.setPlaceholderText(t('ui.nib_widget.bezug_tuner_z_b_gravitas_fnf_nibsmith_b1b8029f'))
        self.nibm_edit   = QLineEdit(); self.nibm_edit.setPlaceholderText(t('ui.nib_widget.nibmeister_person_z_b_mike_masuyama_2a93305d'))
        self.feed_type_edit = QLineEdit(); self.feed_type_edit.setPlaceholderText(t('ui.nib_widget.z_b_standard_ebonit_custom_2d3adc93'))
        self.feed_notes_edit = QTextEdit(); self.feed_notes_edit.setMaximumHeight(50)
        self.feed_notes_edit.setPlaceholderText(t('ui.nib_widget.feed_beschreibung_z_b_ebonit_getunt_fur_mehr_flo_99b4718d'))
        self.stiff_spin  = QSpinBox(); self.stiff_spin.setRange(1,5); self.stiff_spin.setValue(4)
        self.stiff_spin.setSuffix(t('ui.nib_widget.1_sehr_weich_flex_5_sehr_steif_b4e89672'))
        self.feed_spin   = QSpinBox(); self.feed_spin.setRange(1,5); self.feed_spin.setValue(3)
        self.feed_spin.setSuffix(t('ui.nib_widget.1_nano_smooth_5_sehr_rau_28ae9377'))
        self.flex_cb     = QCheckBox(t('ui.nib_widget.flex_vintage_flex_etikett_zusatzlich_zur_steifig_e0ce3826'))
        self.tuning_edit = QTextEdit(); self.tuning_edit.setMaximumHeight(50)
        self.tuning_edit.setPlaceholderText(t('ui.nib_widget.was_wurde_getunt_von_wem_c3853c47'))
        self.notes_edit  = QTextEdit(); self.notes_edit.setMaximumHeight(70)
        fl.addRow(t('ui.nib_widget.spitzname_7f017695'),            self.label_edit)
        fl.addRow(t('ui.nib_widget.feinheit_98dcd30d'),             self.size_edit)
        fl.addRow(t('ui.nib_widget.federmaterial_c512d3f4'),        self.material_edit)
        fl.addRow(t('ui.nib_widget.schliff_grind_15ef43bf'),      self.grind_edit)
        fl.addRow(t('ui.nib_widget.bezug_tuner_bcbbfa49'),        self.source_edit)
        fl.addRow(t('ui.nib_widget.nibmeister_7e6431bb'),           self.nibm_edit)
        fl.addRow(t('ui.nib_widget.feed_typ_c07bb3f2'),             self.feed_type_edit)
        fl.addRow(t('ui.nib_widget.feed_notiz_eec78309'),           self.feed_notes_edit)
        fl.addRow(t('ui.nib_widget.steifigkeit_0c308bb9'),          self.stiff_spin)
        fl.addRow(t('ui.nib_widget.ruckmeldung_194c5054'),          self.feed_spin)
        fl.addRow("",                     self.flex_cb)
        fl.addRow(t('ui.nib_widget.tuning_notiz_9a807219'),         self.tuning_edit)
        fl.addRow(t('ui.nib_widget.allgemeine_notizen_d51d5bc8'),   self.notes_edit)
        body_l.addWidget(grp_unit)

        body_l.addStretch(1)
        scroll.setWidget(body)
        root.addWidget(scroll, 1)

        br = QHBoxLayout(); br.addStretch()
        cancel = QPushButton(t('ui.nib_widget.abbrechen_b583cee4')); cancel.setStyleSheet(BTN_MUTED)
        cancel.clicked.connect(self.reject)
        save = QPushButton(t('ui.nib_widget.speichern_4f68f6cc')); save.setStyleSheet(BTN_SUCCESS)
        save.clicked.connect(self.accept)
        br.addWidget(cancel); br.addWidget(save); root.addLayout(br)

    # ── Format-Picker ──────────────────────────────────────────────────
    def _reload_formats(self, select_id: Optional[int] = None):
        self.format_combo.blockSignals(True)
        self.format_combo.clear()
        self.format_combo.addItem(t('ui.nib_widget.neues_format_anlegen_felder_unten_ausfullen_42353ab8'), None)
        session = get_session()
        try:
            for fmt in session.query(NibFormat).order_by(NibFormat.manufacturer, NibFormat.physical_size).all():
                self.format_combo.addItem(fmt.label, fmt.id)
        finally:
            session.close()
        if select_id is not None:
            ix = self.format_combo.findData(select_id)
            if ix >= 0:
                self.format_combo.setCurrentIndex(ix)
        self.format_combo.blockSignals(False)

    def _on_format_combo_changed(self, _ix: int):
        """Bei gewähltem Format: Felder befüllen + sperren. Bei 'neu': leer + editierbar."""
        fid = self.format_combo.currentData()
        if fid is not None:
            session = get_session()
            try:
                fmt = session.get(NibFormat, fid)
                if fmt:
                    self.fmt_mfr_edit.setText(fmt.manufacturer or "")
                    self.fmt_phys_edit.setText(fmt.physical_size or "")
                    self.fmt_prop_cb.setChecked(bool(fmt.is_proprietary))
                    self.fmt_compat_edit.setPlainText(fmt.compatible_with or "")
                    self.fmt_notes_edit.setPlainText(fmt.notes or "")
            finally:
                session.close()
            for w in self._fmt_inputs:
                w.setEnabled(False)
        else:
            for w in self._fmt_inputs:
                w.setEnabled(True)

    def _load(self):
        n = self.nib
        # Falls keine Format-Verknüpfung: Legacy-Felder als Vorbefüllung des Format-Bereichs.
        if not n.format_id:
            self.fmt_mfr_edit.setText(getattr(n, "manufacturer", "") or "")
            self.fmt_phys_edit.setText(getattr(n, "physical_size", "") or "")
            self.fmt_prop_cb.setChecked(bool(getattr(n, "is_proprietary", False)))
        # Exemplar-Felder
        self.label_edit.setText(getattr(n, "label", "") or "")
        self.size_edit.setText(n.size or "")
        self.material_edit.setText(getattr(n, "material", None) or "")
        self.grind_edit.setText(n.grind or "")
        self.source_edit.setText(getattr(n, "source", None) or "")
        self.nibm_edit.setText(n.nibmeister or "")
        self.feed_type_edit.setText(getattr(n, "feed_type", None) or "")
        self.feed_notes_edit.setPlainText(getattr(n, "feed_notes", None) or "")
        self.stiff_spin.setValue(int(getattr(n, "stiffness_level", 4) or 4))
        self.feed_spin.setValue(int(n.feedback_level or 3))
        self.flex_cb.setChecked(bool(n.is_flexible))
        self.tuning_edit.setPlainText(getattr(n, "tuning_notes", None) or "")
        self.notes_edit.setPlainText(n.notes or "")

    @staticmethod
    def _norm_text(value) -> str:
        return (value or "").strip().lower().replace("no.", "#").replace("no ", "#").replace("nr.", "#")

    # ── API für die Aufrufer ───────────────────────────────────────────
    def resolve_format(self, session) -> Optional[int]:
        """Liefert die format_id für diese Feder.

        Existierendes Format gewählt → dessen id.
        Sonst Format-Duplikat über (Marke, Baugröße, proprietär) – wenn vorhanden
        verwenden, sonst neues NibFormat anlegen. Formate werden bewusst
        dedupliziert (anders als Exemplare).
        """
        fid = self.format_combo.currentData()
        if fid is not None:
            return int(fid)
        mfr = self.fmt_mfr_edit.text().strip()
        phys = self.fmt_phys_edit.text().strip()
        prop = self.fmt_prop_cb.isChecked()
        if not (mfr or phys):
            return None
        existing = None
        for fmt in session.query(NibFormat).all():
            if (self._norm_text(fmt.manufacturer) == self._norm_text(mfr) and
                self._norm_text(fmt.physical_size) == self._norm_text(phys) and
                bool(fmt.is_proprietary) == prop):
                existing = fmt
                break
        if existing:
            # Felder ggf. nachpflegen (Kompatibilität/Notiz), ohne Vorhandenes zu löschen
            new_compat = self.fmt_compat_edit.toPlainText().strip() or None
            new_notes  = self.fmt_notes_edit.toPlainText().strip() or None
            if new_compat and not existing.compatible_with:
                existing.compatible_with = new_compat
            if new_notes and not existing.notes:
                existing.notes = new_notes
            return existing.id
        fmt = NibFormat(
            manufacturer=mfr or "Unbekannt",
            physical_size=phys or None,
            is_proprietary=prop,
            compatible_with=self.fmt_compat_edit.toPlainText().strip() or None,
            notes=self.fmt_notes_edit.toPlainText().strip() or None,
        )
        session.add(fmt); session.flush()
        return fmt.id

    def get_data(self) -> dict:
        """Nur Exemplar-Felder. Aufrufer setzt format_id via resolve_format(session)."""
        return {
            "label":           self.label_edit.text().strip() or None,
            "size":            self.size_edit.text().strip() or None,
            "material":        self.material_edit.text().strip() or None,
            "grind":           self.grind_edit.text().strip() or None,
            "source":          self.source_edit.text().strip() or None,
            "nibmeister":      self.nibm_edit.text().strip() or None,
            "feed_type":       self.feed_type_edit.text().strip() or None,
            "feed_notes":      self.feed_notes_edit.toPlainText().strip() or None,
            "stiffness_level": int(self.stiff_spin.value()),
            "feedback_level":  int(self.feed_spin.value()),
            "is_flexible":     self.flex_cb.isChecked(),
            "tuning_notes":    self.tuning_edit.toPlainText().strip() or None,
            "notes":           self.notes_edit.toPlainText().strip() or None,
            # Legacy-Cache für Filter/Anzeige in alten Code-Pfaden:
            "manufacturer":    self.fmt_mfr_edit.text().strip() or None,
            "physical_size":   self.fmt_phys_edit.text().strip() or None,
            "is_proprietary":  self.fmt_prop_cb.isChecked(),
        }
