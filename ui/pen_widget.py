"""
Füllerverwaltung – CRUD, Tinte einfüllen, Reinigung markieren, Details-Panel.
"""
from datetime import datetime
import csv
from typing import Optional
from pathlib import Path
import shutil
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit, QDialog, QGroupBox, QScrollArea, QMessageBox, QSplitter, QFrame, QMenu, QFileDialog
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPixmap
from database.db import get_session, _data_dir
from database.repositories import (ExpenseRepository, PenNibSetupRepository,
                                   PenRepository)
from logic.pen_service import (collect_sample_comparison_context,
                               find_active_pen_duplicate,
                               find_or_create_nib_format,
                               find_pen_variant, find_similar_nib,
                               single_active_pen_id,
                               sync_purchase_expense_for_pen)
from i18n.translator import format_money, format_date, LocaleService, t
from i18n.qt_i18n import translate_source_text
from database.models import Pen, Ink, InkLoad, Nib, PenNibSetup, Expense
from logic.event_bus import AppEventBus
from logic.budget_export_service import sync_default_outbox_from_session_safely
from logic.media_storage_service import import_pen_image
from ui.ui_scale import scale_px
from ui.theme import btn_accent, btn_primary, btn_secondary
# v0.3.02: Gemeinsame Helfer liegen in ui/pen_common (Re-Export für
# bestehende Nutzer und statische Guards).
from ui.pen_common import (  # noqa: F401
    BLOCKING_STATUSES, FILL_SYSTEM_KEYS, ROTATION_ROLES, ROTATION_THEMES,
    TAG_KEYS, _fill_system_label, _fill_systems, _rotation_roles,
    _rotation_themes, _status_label, _tag_label,
)

# SEC-001: SSRF-Validierung liegt seit v0.3.02 in logic/image_url_security
# (Qt-frei, direkt testbar). Re-Export hält bestehende Importe stabil.
from logic.image_url_security import (  # noqa: F401
    _is_safe_remote_image_url,
    _SafeImageRedirectHandler,
)


class PenWidget(QWidget):

    def __init__(self):
        super().__init__()
        self._setup_ui()
        bus = AppEventBus.instance()
        # Pens can be created outside this widget, e.g. Wishlist → "Als gekauft übernehmen".
        # Listening only to inks_changed left an already-open PenWidget stale until a manual refresh/navigation.
        bus.pens_changed.connect(self.refresh)
        # Usability 3.3 (Briefing): Bilder per Drag & Drop auf die Füllerseite.
        self.setAcceptDrops(True)
        bus.inks_changed.connect(self.refresh)
        bus.nibs_changed.connect(self.refresh)
        self.refresh()

    _IMAGE_SUFFIXES = ('.png', '.jpg', '.jpeg', '.webp', '.bmp')

    def _dropped_image_paths(self, event) -> list:
        md = event.mimeData()
        if not md.hasUrls():
            return []
        return [u.toLocalFile() for u in md.urls()
                if u.isLocalFile() and u.toLocalFile().lower().endswith(self._IMAGE_SUFFIXES)]

    def dragEnterEvent(self, event):
        if self._dropped_image_paths(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        paths = self._dropped_image_paths(event)
        if not paths:
            event.ignore()
            return
        pen_id = self._selected_id()
        if not pen_id:
            QMessageBox.information(self, t('ui.pen_widget.fullerbild_auswahlen_5a1ff15e'), t("ui.pen_widget.drop_select_first"))
            return
        self._set_image_from_path(pen_id, paths[0])
        event.acceptProposedAction()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)
        hdr = QHBoxLayout()
        title = QLabel(t('ui.pen_widget.fuller_94e9d05a'))
        title.setObjectName('page_title')
        hdr.addWidget(title)
        hdr.addStretch()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(t('ui.pen_widget.suchen_231da039'))
        self.search_edit.setFixedWidth(220)
        self.search_edit.textChanged.connect(self._filter)
        hdr.addWidget(self.search_edit)
        add_btn = QPushButton(t('ui.pen_widget.fuller_0c6e26b0'))
        add_btn.setProperty('class', 'primary')
        add_btn.setStyleSheet(btn_primary())
        add_btn.clicked.connect(self._add)
        hdr.addWidget(add_btn)
        import_btn = QPushButton(t('ui.pen_widget.import_e7ffd6f8'))
        import_btn.setStyleSheet('background:#7f8c8d;color:white;border:none;padding:7px 14px;border-radius:5px;font-weight:bold;')
        import_btn.clicked.connect(self._import_pens)
        hdr.addWidget(import_btn)
        copy_btn = QPushButton(t('ui.pen_widget.fuller_kopieren_0fb5ffd0'))
        copy_btn.setStyleSheet(btn_accent())
        copy_btn.clicked.connect(self._copy_pen)
        hdr.addWidget(copy_btn)
        help_btn = QPushButton(t('ui.pen_widget.service_hilfe_26a2c650'))
        help_btn.setStyleSheet(btn_accent())
        help_btn.clicked.connect(self._show_service_help)
        hdr.addWidget(help_btn)
        size_btn = QPushButton(t('ui.pen_widget.groenvergleich_4de65487'))
        size_btn.setStyleSheet(btn_secondary())
        size_btn.clicked.connect(self._show_size_compare)
        hdr.addWidget(size_btn)
        export_btn = QPushButton(t('ui.pen_widget.fuller_exportieren_d7b5b88d'))
        export_btn.setStyleSheet(btn_secondary())
        export_btn.clicked.connect(self._export_pens)
        hdr.addWidget(export_btn)
        from PySide6.QtWidgets import QCheckBox as _QCB
        self._show_archived_cb = _QCB(t('ui.pen_widget.show_archived_label'))
        self._show_archived_cb.setToolTip(t('ui.pen_widget.archivierte_inaktive_fuller_anzeigen_d2a4f389'))
        self._show_archived_cb.toggled.connect(lambda *_: self.refresh())
        hdr.addWidget(self._show_archived_cb)
        root.addLayout(hdr)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(8)
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([t('ui.pen_widget.status_f66ce01f'), t('ui.pen_widget.fuller_e5df3d89'), t('ui.pen_widget.feder_82b25afd'), t('ui.pen_widget.tinte_312ff868'), t('ui.pen_widget.tage_5ced3a25'), t('ui.pen_widget.warnung_64fffe34')])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.clicked.connect(self._on_select)
        self.table.doubleClicked.connect(self._edit)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        from PySide6.QtWidgets import QStackedWidget
        from ui.common import EmptyStateWidget
        self.stack = QStackedWidget()
        self.stack.addWidget(self.table)  # index 0
        self._empty_state = EmptyStateWidget(
            icon="\U0001f58b",
            title=t("ui.pen_widget.empty_title"),
            subtitle=t("ui.pen_widget.empty_subtitle"),
            action_label=t("ui.pen_widget.empty_action"),
            action_slot=self._add,
        )
        self.stack.addWidget(self._empty_state)  # index 1
        ll.addWidget(self.stack)
        btn_row = QHBoxLayout()
        self.edit_btn = self._mk_btn('✏  ' + t('common.edit'), '#f39c12', self._edit, False)
        self.del_btn = self._mk_btn('🗑  ' + t('common.delete'), '#e74c3c', self._delete, False)
        self.load_btn = self._mk_btn(t('ui.pen_widget.fill_button'), '#27ae60', self._load_ink, False)
        self.clean_btn = self._mk_btn('💧  Gereinigt', '#2980b9', self._mark_cleaned, False)
        self.service_btn = self._mk_btn('🔒  Sperren/Service', '#8e44ad', self._service_block, False)
        for b in (self.edit_btn, self.del_btn, self.load_btn, self.clean_btn, self.service_btn):
            btn_row.addWidget(b)
        btn_row.addStretch()
        ll.addLayout(btn_row)
        splitter.addWidget(left)
        self._detail_panel = self._build_detail_panel()
        splitter.addWidget(self._detail_panel)
        splitter.setSizes([760, 360])
        root.addWidget(splitter)

    @staticmethod
    def _mk_btn(text: str, color: str, slot, enabled: bool=True) -> QPushButton:
        b = QPushButton(translate_source_text(text))
        b.setEnabled(enabled)
        b.setStyleSheet(f'background:{color};color:white;border:none;padding:6px 12px;border-radius:5px;')
        b.clicked.connect(slot)
        return b

    def _build_detail_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet('background:white; border-left:1px solid #d5dce6;')
        vl = QVBoxLayout(panel)
        vl.setContentsMargins(16, 16, 16, 16)
        self._detail_title = QLabel(t('ui.pen_widget.fuller_auswahlen_9bdd7270'))
        self._detail_title.setStyleSheet('font-size:16px;font-weight:bold;color:#1e2a38;')
        vl.addWidget(self._detail_title)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameStyle(QFrame.Shape.NoFrame)
        self._detail_body = QWidget()
        self._detail_body_layout = QVBoxLayout(self._detail_body)
        scroll.setWidget(self._detail_body)
        vl.addWidget(scroll)
        ph = QLabel(t('ui.pen_widget.wahle_einen_fuller_aus_der_liste_b81e86ba'))
        ph.setStyleSheet('color:#5f6f72;font-size:13px;')
        ph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._detail_body_layout.addWidget(ph)
        self._detail_body_layout.addStretch()
        return panel

    def refresh(self):
        session = get_session()
        try:
            show_archived = getattr(self, '_show_archived_cb', None) and self._show_archived_cb.isChecked()
            if show_archived:
                pens = PenRepository(session).all_sorted()
            else:
                pens = PenRepository(session).active_sorted()
            cur_id = self._selected_id()
            self.table.setRowCount(len(pens))
            # Einheitlicher Leerzustand wie auf Tinten/Federn/Papier.
            if hasattr(self, "stack"):
                self.stack.setCurrentIndex(1 if not pens else 0)
            for row, pen in enumerate(pens):
                status_txt = t('ui.pen_widget.status_filled') if pen.current_ink_load else t('ui.pen_widget.status_empty')
                if getattr(pen, 'rotation_blocked', False) or getattr(pen, 'availability_status', 'available') in BLOCKING_STATUSES:
                    _status = getattr(pen, 'availability_status', 'blocked')
                    _icon = {'service': '🔧', 'dry_risk': '🧼'}.get(_status, '🔒')
                    status_txt = f"{_icon} {_status_label(_status) or _status}"
                status_item = QTableWidgetItem(status_txt)
                status_item.setData(Qt.ItemDataRole.UserRole, pen.id)
                status_item.setForeground(QColor('#8e44ad' if status_txt.startswith('🔒') else '#27ae60' if pen.current_ink_load else '#5f6f72'))
                self.table.setItem(row, 0, status_item)
                self.table.setItem(row, 1, QTableWidgetItem(f'{pen.brand} {pen.model}'.strip()))
                nib_txt = '—'
                setup = getattr(pen, 'active_nib_setup', None)
                if setup and setup.nib:
                    nib_txt = setup.display_label
                elif pen.nib:
                    nib_txt = pen.nib.display_label
                self.table.setItem(row, 2, QTableWidgetItem(nib_txt))
                warn_txt = ''
                load = pen.current_ink_load
                if load:
                    ink = session.get(Ink, load.ink_id)
                    ink_txt = f'{ink.brand} {ink.name}' if ink else '?'
                    ink_item = QTableWidgetItem(ink_txt)
                    ink_item.setForeground(QColor('#27ae60'))
                    self.table.setItem(row, 3, ink_item)
                    days = load.days_loaded
                    d_item = QTableWidgetItem(str(days))
                    if ink and ink.max_days_in_pen and (days > ink.max_days_in_pen):
                        d_item.setForeground(QColor('#e74c3c'))
                        d_item.setFont(QFont('', -1, QFont.Weight.Bold))
                        warn_txt = 'Reinigung fällig'
                    self.table.setItem(row, 4, d_item)
                else:
                    self.table.setItem(row, 3, QTableWidgetItem('—'))
                    self.table.setItem(row, 4, QTableWidgetItem('—'))
                    warn_txt = ''
                tags_txt = ', '.join((_tag_label(t) or t for t in pen.tags_list))
                if getattr(pen, 'rotation_blocked', False) or getattr(pen, 'availability_status', 'available') in BLOCKING_STATUSES:
                    until = getattr(pen, 'blocked_until', None)
                    blocked_txt = t('ui.pen_widget.rotation_blocked')
                    if until:
                        blocked_txt += ' ' + t('ui.pen_widget.until_suffix', date=format_date(until))
                    warn_txt = (warn_txt + ' · ' if warn_txt else '') + blocked_txt
                if getattr(pen, 'must_include_in_rotation', False):
                    warn_txt = (warn_txt + ' · ' if warn_txt else '') + 'Rotation-Pflicht'
                elif tags_txt:
                    warn_txt = tags_txt
                self.table.setItem(row, 5, QTableWidgetItem(warn_txt or '—'))
                if pen.id == cur_id:
                    self.table.selectRow(row)
        finally:
            session.close()

    def _filter(self, text: str):
        text = text.lower()
        for r in range(self.table.rowCount()):
            vis = any((self.table.item(r, c) and text in self.table.item(r, c).text().lower() for c in range(self.table.columnCount())))
            self.table.setRowHidden(r, not vis)

    def _selected_id(self) -> Optional[int]:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _on_select(self):
        pen_id = self._selected_id()
        enabled = pen_id is not None
        for b in (self.edit_btn, self.del_btn, self.load_btn, self.clean_btn, self.service_btn):
            b.setEnabled(enabled)
        if pen_id:
            self._show_details(pen_id)

    def _show_details(self, pen_id: int):
        session = get_session()
        try:
            pen = session.get(Pen, pen_id)
            if not pen:
                return
            while self._detail_body_layout.count():
                item = self._detail_body_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            self._detail_title.setText(f'{pen.brand} {pen.model}')
            if getattr(pen, 'image_path', None):
                img_path = Path(pen.image_path)
                if img_path.exists():
                    pix = QPixmap(str(img_path))
                    if not pix.isNull():
                        img = QLabel()
                        img.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        img.setPixmap(pix.scaled(300, 180, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                        img.setStyleSheet('background:#f6f8fb;border:1px solid #d5dce6;border-radius:8px;padding:6px;')
                        # Usability 3.4: Klick öffnet die große Bildansicht.
                        img.setCursor(Qt.CursorShape.PointingHandCursor)
                        img.setToolTip(t("common.click_to_zoom"))
                        _title = f'{pen.brand} {pen.model}'.strip()
                        _full = QPixmap(str(img_path))

                        def _open_zoom(event, _pix=_full, _t=_title):
                            from ui.common import ImageZoomDialog
                            ImageZoomDialog(_pix, _t, self).exec()
                        img.mousePressEvent = _open_zoom
                        self._detail_body_layout.addWidget(img)

            def row(label: str, value: str, color: str='#2c3e50'):
                w = QWidget()
                h = QHBoxLayout(w)
                h.setContentsMargins(0, 2, 0, 2)
                lbl = QLabel(f'<b>{translate_source_text(label)}</b>')
                lbl.setStyleSheet('color:#5f6f72; min-width:150px;')
                val = QLabel(translate_source_text(value) if isinstance(value, str) else value or '—')
                val.setStyleSheet(f'color:{color};')
                val.setWordWrap(True)
                h.addWidget(lbl)
                h.addWidget(val, 1)
                self._detail_body_layout.addWidget(w)
            row(t('ui.pen_widget.fullsystem_dae24858'), _fill_system_label(pen.fill_system) or pen.fill_system)
            if getattr(pen, 'rotation_blocked', False) or getattr(pen, 'availability_status', 'available') != 'available':
                until = getattr(pen, 'blocked_until', None)
                status = getattr(pen, 'availability_status', 'blocked')
                status_txt = _status_label(status) or status
                if until:
                    status_txt += ' ' + t('ui.pen_widget.until_suffix', date=format_date(until))
                row(t('ui.pen_widget.status_f66ce01f'), status_txt, '#e74c3c')
                if getattr(pen, 'service_cost', None):
                    row(t('ui.pen_widget.servicekosten_126d7edf'), format_money(pen.service_cost, getattr(pen, 'service_currency', None)), '#8e44ad')
                if getattr(pen, 'service_notes', None):
                    row(t('ui.pen_widget.legacy_exact.text_001'), pen.service_notes, '#8e44ad')
            row(t('ui.pen_widget.fullvolumen_80c36e67'), f'{pen.ink_capacity_ml:g} ml' if getattr(pen, 'ink_capacity_ml', None) else '—')
            row(t('ui.pen_widget.beliebtheit_6d7e4d54'), f"{getattr(pen, 'popularity_rating', 3) or 3}/5")
            role_label = dict(_rotation_roles()).get(getattr(pen, 'rotation_role', None), getattr(pen, 'rotation_role', None) or t('rotation.role_writer'))
            theme_label = dict(_rotation_themes()).get(getattr(pen, 'rotation_theme', None), getattr(pen, 'rotation_theme', None) or t('rotation.theme_auto'))
            row(t('rotation.role_label'), role_label, '#8e44ad')
            row(t('rotation.theme_label'), theme_label, '#34495e')
            if getattr(pen, 'must_include_in_rotation', False):
                row(t('nav.rotation'), t('ui.pen_widget.legacy_exact.text_002'), '#27ae60')
            if getattr(pen, 'fixed_ink', None):
                row(t('ui.pen_widget.legacy_exact.text_003'), f'{pen.fixed_ink.brand} {pen.fixed_ink.name}', '#8e44ad')
            if pen.nib:
                row(t('ui.pen_widget.feder_82b25afd'), pen.nib.display_label, '#8e44ad')
                row(t('ui.pen_widget.legacy_exact.text_004'), 'Proprietär' if pen.nib.effective_is_proprietary else 'Standard / kompatibel')
                if getattr(pen.nib, 'source', None):
                    row(t('ui.pen_widget.bezug_tuner_436b44fb'), pen.nib.source)
                if pen.nib.nibmeister:
                    row(t('ui.pen_widget.nibmeister_995b4e58'), pen.nib.nibmeister)
                stiff = getattr(pen.nib, 'stiffness_level', None)
                if stiff:
                    row(t('ui.nib_widget.steifigkeit_0c308bb9'), f'{stiff}/5')
                if pen.nib.feedback_level:
                    row(t('ui.pen_widget.feder_feedback_52e130c7'), f'{pen.nib.feedback_level}/5')
                if getattr(pen.nib, 'feed_type', None) or getattr(pen.nib, 'feed_notes', None):
                    bits = [pen.nib.feed_type or '', pen.nib.feed_notes or '']
                    row(t('ui.pen_widget.feed_label'), ' · '.join((b for b in bits if b)))
                if getattr(pen.nib, 'tuning_notes', None):
                    row(t('ui.pen_widget.tuning_label'), pen.nib.tuning_notes)
                if pen.nib.format and pen.nib.format.compatible_with:
                    row(t('ui.pen_widget.legacy_exact.text_010'), pen.nib.format.compatible_with, '#16a085')
                if pen.nib.notes:
                    row(t('ui.pen_widget.legacy_exact.text_011'), pen.nib.notes)
            else:
                row(t('ui.pen_widget.feder_82b25afd'), t('ui.pen_widget.legacy_exact.text_012'), '#5f6f72')
            row(t('ui.pen_widget.farbe_76ffe348'), pen.color)
            if getattr(pen, 'compatible_nibs', None):
                row(t('ui.pen_widget.legacy_exact.text_013'), pen.compatible_nibs, '#16a085')
            if getattr(pen, 'incompatible_nibs', None):
                row(t('ui.pen_widget.nicht_kompatibel_357daa34'), pen.incompatible_nibs, '#c0392b')
            if pen.purchase_date:
                row(t('ui.pen_widget.kaufdatum_76cc01cf'), format_date(pen.purchase_date))
            if pen.purchase_price:
                row(t('ui.pen_widget.kaufpreis_6ae12ade'), format_money(pen.purchase_price, getattr(pen, 'purchase_currency', None)))
            if pen.current_market_value:
                row(t('ui.pen_widget.marktwert_6e0161c8'), format_money(pen.current_market_value, getattr(pen, 'market_currency', None)))
            if pen.insurance_value:
                row(t('ui.pen_widget.versicherungswert_8d05db42'), format_money(pen.insurance_value, getattr(pen, 'insurance_currency', None)))
            dims = []
            if pen.length_mm:
                dims.append(t('ui.pen_widget.dimension_closed', value=pen.length_mm))
            if getattr(pen, 'length_uncapped_mm', None):
                dims.append(t('ui.pen_widget.dimension_open', value=pen.length_uncapped_mm))
            if getattr(pen, 'length_posted_mm', None):
                dims.append(t('ui.pen_widget.dimension_posted', value=pen.length_posted_mm))
            if pen.diameter_mm:
                dims.append(f'{pen.diameter_mm:g} mm Ø max')
            if getattr(pen, 'section_diameter_mm', None):
                dims.append(f'{pen.section_diameter_mm:g} mm Griff')
            if pen.weight_g:
                dims.append(f'{pen.weight_g:g} g')
            if dims:
                row(t('ui.pen_widget.abmessungen_73a105d5'), ' | '.join(dims))
            if pen.tags_list:
                row(t('ui.pen_widget.tags_f9c91062'), ', '.join((_tag_label(t) or t for t in pen.tags_list)), '#3498db')
            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.HLine)
            sep.setStyleSheet('color:#eee; margin:6px 0;')
            self._detail_body_layout.addWidget(sep)
            load = pen.current_ink_load
            if load:
                ink = session.get(Ink, load.ink_id)
                if ink:
                    row(t('pen.current_ink'), f'{ink.brand} {ink.name}', '#27ae60')
                    days = load.days_loaded
                    color = '#e74c3c' if ink.max_days_in_pen and days > ink.max_days_in_pen else '#2c3e50'
                    row(t('ui.pen_widget.legacy_exact.text_023'), t('ui.dashboard_widget.days_value', days=days), color)
                    if ink.max_days_in_pen:
                        row(t('ui.dashboard_widget.max_tage_fd6d6777'), str(ink.max_days_in_pen))
            else:
                row(t('ui.pen_widget.legacy_exact.text_025'), t('pen.no_ink'), '#5f6f72')
            self._add_enthusiast_actions(pen.id)
            for note_label, note_text, nc in ((t('pen.writing_feel'), pen.writing_feel_notes, '#2c3e50'), ('⚠ ' + t('pen.problems'), pen.problem_notes, '#e74c3c'), (t('pen.cleaning'), pen.cleaning_notes, '#5f6f72')):
                if note_text:
                    lbl = QLabel(f'<b>{note_label}:</b><br>{note_text}')
                    lbl.setStyleSheet(f'color:{nc}; font-size:12px; padding:4px 0;')
                    lbl.setWordWrap(True)
                    self._detail_body_layout.addWidget(lbl)
            self._add_expense_history(session, pen.id)
            self._detail_body_layout.addStretch()
        finally:
            session.close()

    def _add_enthusiast_actions(self, pen_id: int) -> None:
        """Kontextnahe Sammler-Aktionen, ohne die Fülleransicht zu überladen."""
        box = QGroupBox(t("pen_detail.enthusiast_actions"))
        layout = QVBoxLayout(box)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        row1 = QHBoxLayout()
        add_sample = QPushButton(t("pen_detail.sample_add_for_pen"))
        add_sample.clicked.connect(lambda checked=False, pid=pen_id: self._add_writing_sample_for_pen(pid))
        compare = QPushButton(t("pen_detail.sample_compare_for_pen"))
        compare.clicked.connect(lambda checked=False, pid=pen_id: self._compare_writing_samples_for_pen(pid))
        row1.addWidget(add_sample)
        row1.addWidget(compare)
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        history = QPushButton(t("pen_detail.nib_history_for_pen"))
        history.clicked.connect(lambda checked=False, pid=pen_id: self._show_nib_history_for_pen(pid))
        setup = QPushButton(t("pen_detail.nib_setup_change"))
        setup.clicked.connect(lambda checked=False, pid=pen_id: self._edit_pen_by_id(pid))
        row2.addWidget(history)
        row2.addWidget(setup)
        layout.addLayout(row2)
        self._detail_body_layout.addWidget(box)

    def _add_writing_sample_for_pen(self, pen_id: int) -> None:
        from database.models import WritingSample
        from ui.writing_samples_widget import WritingSampleDialog
        session = get_session()
        try:
            pen = session.get(Pen, pen_id)
            if not pen:
                return
            load = getattr(pen, "current_ink_load", None)
            defaults = {
                "pen_id": pen.id,
                "ink_id": getattr(load, "ink_id", None) if load else None,
                "nib_id": getattr(pen, "nib_id", None),
            }
            dlg = WritingSampleDialog(self, session=session, defaults=defaults)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                sample = WritingSample(**dlg.get_data())
                session.add(sample)
                session.commit()
                AppEventBus.instance().emit_samples()
                self._show_details(pen_id)
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, t('ui.pen_widget.fehler_46938af3'), str(exc))
        finally:
            session.close()

    def _compare_writing_samples_for_pen(self, pen_id: int) -> None:
        from database.models import WritingSample
        from logic.writing_sample_service import compare_samples
        from ui.writing_samples_widget import WritingSampleComparisonDialog
        session = get_session()
        try:
            samples, pens, inks, papers = collect_sample_comparison_context(session, pen_id)
            if len(samples) < 2:
                QMessageBox.information(self, t("writing_samples.compare_title"), t("pen_detail.sample_need_two_for_pen"))
                return
            dlg = WritingSampleComparisonDialog(self, comparison=compare_samples(samples, pens, inks, papers))
            dlg.exec()
        finally:
            session.close()

    def _show_nib_history_for_pen(self, pen_id: int) -> None:
        from logic.enthusiast_lab_service import nib_history_rows
        session = get_session()
        try:
            pen = session.get(Pen, pen_id)
            if not pen:
                return
            setups = PenNibSetupRepository(session).for_pen(pen_id)
            rows = nib_history_rows([pen], setups)
            if not rows:
                QMessageBox.information(self, t("pen_detail.nib_history_title"), t("pen_detail.nib_history_empty"))
                return
            dlg = QDialog(self)
            dlg.setWindowTitle(t("pen_detail.nib_history_title"))
            dlg.resize(scale_px(760), scale_px(360))
            root = QVBoxLayout(dlg)
            table = QTableWidget()
            headers = [
                t("pen_detail.nib_history_headers.nib"),
                t("pen_detail.nib_history_headers.installed"),
                t("pen_detail.nib_history_headers.removed"),
                t("pen_detail.nib_history_headers.active"),
                t("pen_detail.nib_history_headers.days"),
                t("pen_detail.nib_history_headers.notes"),
            ]
            table.setColumnCount(len(headers))
            table.setHorizontalHeaderLabels(headers)
            table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            table.setAlternatingRowColors(True)
            table.setRowCount(len(rows))
            for r, row in enumerate(rows):
                values = [
                    row.nib_label,
                    format_date(row.installed_date) if row.installed_date else "—",
                    format_date(row.removed_date) if row.removed_date else "—",
                    t("common.yes") if row.active else t("common.no"),
                    "—" if row.days_installed is None else str(row.days_installed),
                    row.notes or "—",
                ]
                for c, value in enumerate(values):
                    table.setItem(r, c, QTableWidgetItem(value))
            root.addWidget(table)
            buttons = QHBoxLayout(); buttons.addStretch()
            close = QPushButton(t("common.ok")); close.clicked.connect(dlg.accept)
            buttons.addWidget(close); root.addLayout(buttons)
            dlg.exec()
        finally:
            session.close()

    def _add_expense_history(self, session, pen_id: int):
        """Zeigt alle Ausgaben/Buchungen dieses Füllers unten im Detailbereich."""
        expenses = ExpenseRepository(session).for_pen(pen_id)
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet('color:#eee; margin:10px 0;')
        self._detail_body_layout.addWidget(sep)
        title = QLabel(t('ui.pen_widget.buchungshistorie_65d20c39'))
        title.setStyleSheet('font-size:14px;color:#1e2a38;padding-top:4px;')
        self._detail_body_layout.addWidget(title)
        if not expenses:
            empty = QLabel(t('ui.pen_widget.noch_keine_ausgaben_buchungen_mit_diesem_fuller__a011fee5'))
            empty.setStyleSheet('color:#5f6f72;font-size:12px;')
            empty.setWordWrap(True)
            self._detail_body_layout.addWidget(empty)
            return
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels([t('ui.pen_widget.datum_54b31ac2'), t('ui.pen_widget.typ_25e50910'), t('ui.pen_widget.beschreibung_cd6cfc57'), t('ui.pen_widget.betrag_3784bbd0'), t('ui.pen_widget.total_abbd57c9')])
        table.setRowCount(len(expenses))
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.setMinimumHeight(min(230, 34 + 28 * len(expenses)))
        table.setMaximumHeight(min(260, 38 + 30 * len(expenses)))
        type_labels = {'pen': t('ui.pen_widget.expense_type_purchase'), 'service': t('expenses.categories.service'), 'ink': t('expenses.categories.ink'), 'nib': t('expenses.categories.nib'), 'paper': t('expenses.categories.paper'), 'accessory': t('expenses.categories.accessory'), 'shipping': t('expenses.categories.shipping'), 'customs': t('expenses.categories.customs'), 'other': t('expenses.categories.other')}
        total_by_currency = {}
        for row_idx, exp in enumerate(expenses):
            date_txt = format_date(exp.purchase_date) if exp.purchase_date else '—'
            typ_txt = type_labels.get(exp.item_type, exp.item_type or '—')
            desc_txt = exp.description or exp.vendor or exp.order_number or '—'
            currency = exp.currency or 'CHF'
            total = exp.total or 0.0
            total_by_currency[currency] = total_by_currency.get(currency, 0.0) + total
            values = [date_txt, typ_txt, desc_txt, f'{currency} {exp.amount or 0.0:.2f}', f'{currency} {total:.2f}']
            for col, val in enumerate(values):
                item = QTableWidgetItem(val)
                if exp.item_type == 'service':
                    item.setForeground(QColor('#8e44ad'))
                elif exp.item_type == 'pen':
                    item.setForeground(QColor('#2c3e50'))
                table.setItem(row_idx, col, item)
        hh = table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self._detail_body_layout.addWidget(table)
        totals = ' · '.join((f'{cur} {amount:.2f}' for cur, amount in sorted(total_by_currency.items())))
        total_lbl = QLabel(t('ui.pen_widget.total_bookings_sum', total=totals))
        total_lbl.setStyleSheet('color:#2c3e50;font-weight:bold;padding:4px 0;')
        self._detail_body_layout.addWidget(total_lbl)

    def _export_pens(self):
        path, _ = QFileDialog.getSaveFileName(self, t('ui.pen_widget.fuller_kenndaten_exportieren_ea57a5a0'), 'fueller_export.csv', t('ui.pen_widget.csv_dateien_csv_a2c5e427'))
        if not path:
            return
        session = get_session()
        try:
            pens = PenRepository(session).all_sorted()
            cols = ['id', 'brand', 'model', 'color', 'fill_system', 'status', 'rotation_blocked', 'current_ink', 'current_ink_since', 'current_ink_days', 'nib_manufacturer', 'nib_size', 'nib_physical_size', 'nib_material', 'nib_grind', 'purchase_date', 'purchase_price', 'purchase_currency', 'current_market_value', 'market_currency', 'insurance_value', 'insurance_currency', 'length_mm', 'length_uncapped_mm', 'length_posted_mm', 'diameter_mm', 'section_diameter_mm', 'weight_g', 'ink_capacity_ml', 'popularity_rating', 'must_include_in_rotation', 'rotation_role', 'rotation_theme', 'fixed_ink', 'tags', 'service_start_date', 'service_days', 'blocked_until', 'service_cost', 'writing_feel_notes', 'problem_notes', 'cleaning_notes', 'service_notes', 'compatible_nibs', 'incompatible_nibs', 'image_path']
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(cols)
                for pen in pens:
                    load = pen.current_ink_load
                    current_ink = ''
                    current_since = ''
                    current_days = ''
                    if load and load.ink:
                        current_ink = f'{load.ink.brand} {load.ink.name}'
                        current_since = load.loaded_date
                        current_days = load.days_loaded
                    nib = pen.nib
                    fixed = pen.fixed_ink
                    writer.writerow([pen.id, pen.brand, pen.model, pen.color, pen.fill_system, getattr(pen, 'availability_status', 'available'), getattr(pen, 'rotation_blocked', False), current_ink, current_since, current_days, getattr(nib, 'manufacturer', None) if nib else None, getattr(nib, 'size', None) if nib else None, getattr(nib, 'physical_size', None) if nib else None, getattr(nib, 'material', None) if nib else None, getattr(nib, 'grind', None) if nib else None, pen.purchase_date, pen.purchase_price, getattr(pen, 'purchase_currency', None), pen.current_market_value, getattr(pen, 'market_currency', None), pen.insurance_value, getattr(pen, 'insurance_currency', None), pen.length_mm, getattr(pen, 'length_uncapped_mm', None), getattr(pen, 'length_posted_mm', None), pen.diameter_mm, getattr(pen, 'section_diameter_mm', None), pen.weight_g, pen.ink_capacity_ml, getattr(pen, 'popularity_rating', None), getattr(pen, 'must_include_in_rotation', False), getattr(pen, 'rotation_role', None), getattr(pen, 'rotation_theme', None), f'{fixed.brand} {fixed.name}' if fixed else '', pen.tags, getattr(pen, 'service_start_date', None), getattr(pen, 'service_days', None), getattr(pen, 'blocked_until', None), getattr(pen, 'service_cost', None), pen.writing_feel_notes, pen.problem_notes, pen.cleaning_notes, getattr(pen, 'service_notes', None), getattr(pen, 'compatible_nibs', None), getattr(pen, 'incompatible_nibs', None), getattr(pen, 'image_path', None)])
            QMessageBox.information(self, t('ui.pen_widget.export_849d8fb3'), t('ui.pen_widget.exported_pen_data', path=path))
        except Exception as e:
            QMessageBox.critical(self, t('ui.pen_widget.exportfehler_fa559eec'), str(e))
        finally:
            session.close()

    def _show_service_help(self):
        fs = None
        pen_id = self._selected_id()
        if pen_id:
            session = get_session()
            try:
                pen = session.get(Pen, pen_id)
                fs = pen.fill_system if pen else None
            finally:
                session.close()
        dlg = ServiceHelpDialog(self, fs)
        dlg.exec()

    def _show_size_compare(self):
        dlg = SizeCompareDialog(self)
        dlg.exec()

    def _context_menu(self, pos):
        row = self.table.rowAt(pos.y())
        if row >= 0:
            self.table.selectRow(row)
            self._on_select()
        menu = QMenu(self)
        add = menu.addAction(t('ui.pen_widget.fuller_hinzufugen_0637c395'))
        edit = menu.addAction(t('ui.pen_widget.bearbeiten_9003f0df'))
        copy = menu.addAction(t('ui.pen_widget.fuller_kopieren_1dab7c9b'))
        load = menu.addAction(t('ui.pen_widget.tinte_einfullen_4b5d3bbe'))
        clean = menu.addAction(t('ui.pen_widget.als_gereinigt_markieren_99dced1b'))
        block = menu.addAction(t('ui.pen_widget.sperren_service_eintragen_71ed54d3'))
        unblock = menu.addAction(t('ui.pen_widget.sperre_aufheben_b05a8988'))
        img_action = menu.addAction(t('ui.pen_widget.bild_hochladen_andern_ff3a4eb2'))
        help_action = menu.addAction(t('ui.pen_widget.service_hilfe_zum_fullsystem_f464415b'))
        sizes_action = menu.addAction(t('ui.pen_widget.groenvergleich_offnen_ab509191'))
        delete = menu.addAction(t('ui.pen_widget.loschen_2d30d900'))
        has_selection = self._selected_id() is not None
        pen_is_active = True
        if has_selection:
            _s = get_session()
            try:
                _p = _s.get(Pen, self._selected_id())
                pen_is_active = bool(_p.is_active) if _p else True
            finally:
                _s.close()
        archive_act = menu.addAction(t('ui.pen_widget.archive_button') if pen_is_active else t('ui.pen_widget.restore_button'))
        for a in (edit, copy, load, clean, block, unblock, img_action, help_action, delete, archive_act):
            a.setEnabled(has_selection)
        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if action == add:
            self._add()
        elif action == edit:
            self._edit()
        elif action == copy:
            self._copy_pen()
        elif action == load:
            self._load_ink()
        elif action == clean:
            self._mark_cleaned()
        elif action == block:
            self._service_block()
        elif action == unblock:
            self._unblock_pen()
        elif action == img_action:
            self._upload_image_for_selected()
        elif action == help_action:
            self._show_service_help()
        elif action == sizes_action:
            self._show_size_compare()
        elif action == delete:
            self._delete()
        elif action == archive_act:
            self._toggle_archive_pen()

    def _upload_image_for_selected(self):
        pen_id = self._selected_id()
        if not pen_id:
            return
        path, _ = QFileDialog.getOpenFileName(self, t('ui.pen_widget.fullerbild_auswahlen_5a1ff15e'), str(Path.home()), t('ui.pen_widget.bilder_png_jpg_jpeg_webp_bmp_0a511660'))
        if not path:
            return
        self._set_image_from_path(pen_id, path)

    def _set_image_from_path(self, pen_id: int, path: str):
        """Importiert ein Bild zentral in ``data/media/pens/<Füller>/images``."""
        session = get_session()
        try:
            pen = session.get(Pen, pen_id)
            if not pen:
                return
            imported = import_pen_image(
                _data_dir(),
                path,
                pen_id=pen.id,
                brand=pen.brand,
                model=pen.model,
            )
            pen.image_path = imported or str(path)
            pen.updated_at = datetime.now()
            session.commit()
            sync_default_outbox_from_session_safely(session)
            AppEventBus.instance().pens_changed.emit()
            AppEventBus.instance().expenses_changed.emit()
            self.refresh()
            self._show_details(pen_id)
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, t('ui.pen_widget.fehler_46938af3'), str(e))
        finally:
            session.close()

    def _store_pen_image_if_needed(self, pen: Pen) -> None:
        """Bild in die verwaltete Medienablage übernehmen – niemals fatal.

        v0.2.87: Der Import kann scheitern (Netzfehler, Timeout, Datei zu groß,
        fehlende Schreibrechte). Vorher riss die Exception die gesamte
        Transaktion mit: Der Nutzer verlor den kompletten, frisch eingetippten
        Füller, weil ein *kosmetischer* Bild-Download fehlschlug. Jetzt wird der
        Fehler gemerkt, der ursprüngliche Pfad/die URL bleibt am Datensatz, und
        der Aufrufer zeigt nach erfolgreichem Commit einen Hinweis.
        """
        self._last_media_warning = None
        raw = getattr(pen, 'image_path', None)
        if not raw:
            return
        try:
            source = self._prefetch_remote_image(raw)
            imported = import_pen_image(_data_dir(), source, pen_id=pen.id, brand=pen.brand, model=pen.model)
        except Exception as exc:  # noqa: BLE001 - Import darf den Datensatz nie kippen
            self._last_media_warning = str(exc)
            return
        if imported:
            pen.image_path = imported

    def _prefetch_remote_image(self, raw: str):
        """URLs im Worker-Thread laden, danach lokal importieren (v0.2.88).

        Vorher lief der Download synchron im GUI-Thread und fror die App bis
        zum Timeout ein. Jetzt übernimmt ``ui.media_download`` den Netzteil mit
        Fortschrittsdialog und Abbruch; der Media-Service sieht nur noch einen
        lokalen Pfad. Nicht-URLs werden unverändert durchgereicht.
        """
        text = str(raw or '').strip()
        if not text.startswith(('http://', 'https://')):
            return raw
        from ui.media_download import download_image_to
        import tempfile
        tmp_dir = Path(tempfile.mkdtemp(prefix='fpm_img_'))
        self._temp_media_dirs = getattr(self, '_temp_media_dirs', [])
        self._temp_media_dirs.append(tmp_dir)
        return download_image_to(self, text, tmp_dir / 'download.img')

    def _cleanup_temp_media(self) -> None:
        import shutil
        for folder in getattr(self, '_temp_media_dirs', []):
            try:
                shutil.rmtree(folder, ignore_errors=True)
            except Exception:
                pass
        self._temp_media_dirs = []

    def _warn_media_import_failed(self) -> None:
        """Nach dem Commit über einen fehlgeschlagenen Bildimport informieren."""
        self._cleanup_temp_media()
        message = getattr(self, '_last_media_warning', None)
        if not message:
            return
        self._last_media_warning = None
        QMessageBox.warning(
            self,
            t('media.import_failed_title'),
            t('media.import_failed_body', error=message),
        )

    def _add(self):
        dlg = PenDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            session = get_session()
            try:
                data = dlg.get_data()
                if not data.get('nib_id') and dlg.should_create_nib():
                    data['nib_id'] = self._resolve_nib(session, dlg)
                pen = Pen(**data)
                session.add(pen)
                session.flush()
                self._store_pen_image_if_needed(pen)
                self._sync_pen_nib_setup(session, pen, dlg)
                _sync_purchase_expense_for_pen(session, pen)
                session.commit()
                AppEventBus.instance().pens_changed.emit()
                self.refresh()
                self._warn_media_import_failed()
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, t('ui.pen_widget.fehler_46938af3'), str(e))
            finally:
                session.close()

    def _edit(self, *args):
        pen_id = self._selected_id()
        if not pen_id:
            return
        self._edit_pen_by_id(pen_id)

    def _edit_pen_by_id(self, pen_id: int):
        session = get_session()
        try:
            pen = session.get(Pen, pen_id)
            if not pen:
                return
            dlg = PenDialog(self, pen)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                data = dlg.get_data()
                if not data.get('nib_id') and dlg.should_create_nib():
                    data['nib_id'] = self._resolve_nib(session, dlg, getattr(pen, 'nib_id', None))
                for k, v in data.items():
                    setattr(pen, k, v)
                pen.updated_at = datetime.now()
                session.flush()
                self._store_pen_image_if_needed(pen)
                self._sync_pen_nib_setup(session, pen, dlg)
                _sync_purchase_expense_for_pen(session, pen)
                session.commit()
                AppEventBus.instance().pens_changed.emit()
                self.refresh()
                self._show_details(pen_id)
                self._warn_media_import_failed()
        except Exception as e:
            QMessageBox.critical(self, t('ui.pen_widget.fehler_46938af3'), str(e))
        finally:
            session.close()

    def _import_pens(self):
        path, _ = QFileDialog.getOpenFileName(self, t('ui.pen_widget.fuller_kenndaten_importieren_c9cbdc9f'), '', t('ui.pen_widget.csv_dateien_csv_a2c5e427'))
        if not path:
            return
        session = get_session()
        added = updated = skipped = 0
        errors = []

        def to_float(v):
            # v0.2.94: derselbe locale-sichere Parser wie in der GUI, damit
            # "1,234.56" oder "1'234.56" nicht als Faktor-100-Fehler landen.
            return LocaleService.instance().parse_number(str(v)) if str(v).strip() else None

        def to_int(v, default=None):
            parsed = LocaleService.instance().parse_number(str(v)) if str(v).strip() else None
            return int(parsed) if parsed is not None else default

        def to_date(v):
            """Datumstring in mehreren Formaten parsen: ISO, DD.MM.YYYY, MM/DD/YYYY, YYYY/MM/DD."""
            if not v or not str(v).strip():
                return None
            s = str(v).strip()
            for fmt in ('%Y-%m-%d', '%d.%m.%Y', '%m/%d/%Y', '%Y/%m/%d', '%d-%m-%Y', '%d/%m/%Y', '%Y-%m-%dT%H:%M:%S', '%d.%m.%Y %H:%M'):
                try:
                    return datetime.strptime(s, fmt)
                except ValueError:
                    continue
            return None
        try:
            from ui.common import ImportPreviewDialog
            preview_results = []
            with open(path, newline='', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for n, row in enumerate(reader, start=2):
                    brand = (row.get('brand') or row.get('Marke') or '').strip()
                    model = (row.get('model') or row.get('Modell') or '').strip()
                    if not brand or not model:
                        preview_results.append({'line': n, 'label': f'Zeile {n}', 'status': 'error', 'msg': t('ui.pen_widget.import_missing_brand_model')})
                        continue
                    date_raw = row.get('purchase_date') or row.get('Kaufdatum') or ''
                    date_val = to_date(date_raw)
                    date_msg = f"Kaufdatum unbekannt: '{date_raw}' → wird ignoriert" if date_raw and (not date_val) else ''
                    fs = (row.get('fill_system') or row.get('Füllsystem') or '').strip().lower()
                    fs_valid = ['piston', 'vac', 'converter', 'cartridge', 'eyedropper']
                    fs_msg = f"Füllsystem '{fs}' unbekannt → converter" if fs and fs not in fs_valid else ''
                    msgs = [m for m in [date_msg, fs_msg] if m]
                    status = 'warn' if msgs else 'ok'
                    preview_results.append({'line': n, 'label': f'{brand} {model}', 'status': status, 'msg': ' | '.join(msgs) if msgs else 'OK'})
            if not preview_results:
                QMessageBox.information(self, t('ui.pen_widget.import_98efcbc7'), t('ui.pen_widget.keine_gultigen_zeilen_in_der_csv_datei_gefunden_37f1109b'))
                return
            dlg = ImportPreviewDialog(preview_results, t('ui.pen_widget.import_preview_title'), self)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return
            importable_lines = {r['line'] for r in preview_results if r['status'] in ('ok', 'warn')}
            with open(path, newline='', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for n, row in enumerate(reader, start=2):
                    if n not in importable_lines:
                        skipped += 1
                        continue
                    try:
                        brand = (row.get('brand') or row.get('Marke') or '').strip()
                        model = (row.get('model') or row.get('Modell') or '').strip()
                        color = (row.get('color') or row.get('Farbe') or '').strip() or None
                        capacity = to_float(row.get('ink_capacity_ml') or row.get('Füllgröße') or row.get('Füllvolumen'))
                        pen = find_pen_variant(session, brand, model, color, capacity)
                        data = dict(brand=brand, model=model, color=color, ink_capacity_ml=capacity, fill_system=(row.get('fill_system') or row.get('Füllsystem') or 'converter').strip() or 'converter', purchase_price=to_float(row.get('purchase_price') or row.get('Kaufpreis')), purchase_currency=(row.get('purchase_currency') or row.get('Kaufpreis-Währung') or LocaleService.instance().currency).strip()[:3].upper() or None, current_market_value=to_float(row.get('current_market_value') or row.get('Marktwert')), market_currency=(row.get('market_currency') or row.get('Marktwert-Währung') or row.get('purchase_currency') or LocaleService.instance().currency).strip()[:3].upper() or None, insurance_value=to_float(row.get('insurance_value') or row.get('Versicherungswert')), insurance_currency=(row.get('insurance_currency') or row.get('Versicherungswert-Währung') or LocaleService.instance().currency).strip()[:3].upper() or None, length_mm=to_float(row.get('length_mm') or row.get('Länge geschlossen')), length_uncapped_mm=to_float(row.get('length_uncapped_mm') or row.get('Länge offen')), length_posted_mm=to_float(row.get('length_posted_mm') or row.get('Länge gepostet')), diameter_mm=to_float(row.get('diameter_mm') or row.get('Durchmesser')), section_diameter_mm=to_float(row.get('section_diameter_mm') or row.get('Griffdurchmesser')), weight_g=to_float(row.get('weight_g') or row.get('Gewicht')), popularity_rating=to_int(row.get('popularity_rating') or row.get('Beliebtheit'), 3), rotation_role=(row.get('rotation_role') or row.get('Rotationsrolle') or 'writer').strip() or 'writer', rotation_theme=(row.get('rotation_theme') or row.get('Standard-Thema') or row.get('Thema') or '').strip() or None, tags=(row.get('tags') or row.get('Tags') or '').strip() or None, writing_feel_notes=(row.get('writing_feel_notes') or row.get('Schreibgefühl') or '').strip() or None, problem_notes=(row.get('problem_notes') or row.get('Probleme') or '').strip() or None, cleaning_notes=(row.get('cleaning_notes') or row.get('Reinigung') or '').strip() or None, purchase_date=to_date(row.get('purchase_date') or row.get('Kaufdatum')))
                        if pen:
                            for k, v in data.items():
                                setattr(pen, k, v)
                            pen.updated_at = datetime.now()
                            updated += 1
                        else:
                            pen = Pen(**data)
                            session.add(pen)
                            session.flush()
                            added += 1
                        _sync_purchase_expense_for_pen(session, pen)
                    except Exception as e:
                        errors.append(f'Zeile {n}: {e}')
            session.commit()
            AppEventBus.instance().pens_changed.emit()
            msg = t('ui.pen_widget.import_done', added=added, updated=updated, skipped=skipped)
            if errors:
                msg += t('ui.pen_widget.import_errors', errors='\n'.join(errors[:20]))
            QMessageBox.information(self, t('ui.pen_widget.import_98efcbc7'), msg)
            self.refresh()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, t('ui.pen_widget.importfehler_7d3aac6c'), str(e))
        finally:
            session.close()

    def _copy_pen(self):
        """Kopiert einen Füller als neues Sammlungsobjekt.

        Technische Kenndaten, Maße, Feder- und Bildverknüpfung werden übernommen.
        Kaufpreis, Marktwert und Versicherungswert können im Dialog neu eingetragen werden.
        Dubletten werden anhand Marke + Modell + Farbe + Füllvolumen erkannt.
        """
        pen_id = self._selected_id()
        if not pen_id:
            QMessageBox.information(self, t('ui.pen_widget.fuller_wahlen_9c9feb21'), t('ui.pen_widget.bitte_zuerst_einen_fuller_auswahlen_92d03e90'))
            return
        session = get_session()
        try:
            src = session.get(Pen, pen_id)
            if not src:
                return
            clone = Pen(brand=src.brand, model=src.model, color=src.color, fill_system=src.fill_system, purchase_date=datetime.now(), purchase_price=None, current_market_value=None, insurance_value=None, length_mm=src.length_mm, length_uncapped_mm=getattr(src, 'length_uncapped_mm', None), length_posted_mm=getattr(src, 'length_posted_mm', None), diameter_mm=src.diameter_mm, section_diameter_mm=getattr(src, 'section_diameter_mm', None), weight_g=src.weight_g, tags=src.tags, rotation_role=getattr(src, 'rotation_role', None), rotation_theme=getattr(src, 'rotation_theme', None), writing_feel_notes=src.writing_feel_notes, problem_notes=src.problem_notes, cleaning_notes=src.cleaning_notes, image_path=src.image_path, is_active=True, availability_status='available', rotation_blocked=False, nib_id=src.nib_id, ink_capacity_ml=getattr(src, 'ink_capacity_ml', None), popularity_rating=getattr(src, 'popularity_rating', 3), must_include_in_rotation=False, fixed_ink_id=getattr(src, 'fixed_ink_id', None), compatible_nibs=getattr(src, 'compatible_nibs', None), incompatible_nibs=getattr(src, 'incompatible_nibs', None))
            dlg = PenDialog(self, clone)
            dlg.setWindowTitle(t('ui.pen_widget.fuller_kopieren_preise_neu_eintragen_abd7ac4d'))
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return
            data = dlg.get_data()
            dup = find_active_pen_duplicate(session, data)
            if dup and dup.id != pen_id:
                res = QMessageBox.question(self, t('ui.pen_widget.dublettenverdacht_a73f57c9'), t('ui.pen_widget.es_gibt_bereits_einen_aktiven_fuller_mit_gleiche_0754937a'), QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if res != QMessageBox.StandardButton.Yes:
                    return
            if not data.get('nib_id') and dlg.should_create_nib():
                data['nib_id'] = self._resolve_nib(session, dlg, getattr(src, 'nib_id', None))
            pen = Pen(**data)
            session.add(pen)
            session.flush()
            self._store_pen_image_if_needed(pen)
            _sync_purchase_expense_for_pen(session, pen)
            session.commit()
            AppEventBus.instance().pens_changed.emit()
            self.refresh()
            QMessageBox.information(self, t('ui.pen_widget.fuller_kopiert_f971b21d'), t('ui.pen_widget.fuller_wurde_als_neues_exemplar_angelegt_der_neu_c1f65774'))
            self._warn_media_import_failed()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, t('ui.pen_widget.fehler_46938af3'), str(e))
        finally:
            session.close()

    def _delete(self):
        pen_id = self._selected_id()
        if not pen_id:
            return
        session = get_session()
        try:
            pen = session.get(Pen, pen_id)
            if not pen:
                return
            if QMessageBox.question(self, t('ui.pen_widget.loschen_343be183'), t('ui.pen_widget.confirm_delete_pen', pen=f'{pen.brand} {pen.model}'), QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                session.delete(pen)
                session.commit()
                AppEventBus.instance().pens_changed.emit()
                self.refresh()
                self._clear_details()
        finally:
            session.close()

    def _quick_pen_id(self) -> int | None:
        """Füller für Schnellaktionen bestimmen.

        Toolbar/Dashboard rufen Befüllen/Reinigen auch ohne Tabellen-Selektion
        auf. Statt stumm abzubrechen: bei genau einem aktiven Füller diesen
        automatisch verwenden, sonst freundlich zur Auswahl auffordern.
        """
        pen_id = self._selected_id()
        if pen_id:
            return pen_id
        session = get_session()
        try:
            single = single_active_pen_id(session)
        finally:
            session.close()
        if single is not None:
            return single
        QMessageBox.information(
            self,
            t("ui.pen_widget.quick_no_selection_title"),
            t("ui.pen_widget.quick_select_pen_hint"),
        )
        return None

    def _load_ink(self):
        pen_id = self._quick_pen_id()
        if not pen_id:
            return
        session = get_session()
        try:
            pen = session.get(Pen, pen_id)
            if pen and (getattr(pen, 'rotation_blocked', False) or getattr(pen, 'availability_status', 'available') in BLOCKING_STATUSES):
                QMessageBox.warning(self, t('ui.pen_widget.gesperrt_aab7ad8e'), t('ui.pen_widget.dieser_fuller_ist_gesperrt_in_service_und_kann_n_daa39506'))
                return
        finally:
            session.close()
        dlg = LoadInkDialog(self, pen_id)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh()
            self._show_details(pen_id)

    def _mark_cleaned(self):
        pen_id = self._quick_pen_id()
        if not pen_id:
            return
        session = get_session()
        try:
            pen = session.get(Pen, pen_id)
            load = pen.current_ink_load if pen else None
            if not load:
                QMessageBox.information(self, t('ui.pen_widget.info_783b14f6'), t('ui.pen_widget.dieser_fuller_hat_keine_aktive_tinte_ac58b02f'))
                return
            ink = session.get(Ink, load.ink_id)
            ink_name = f'{ink.brand} {ink.name}' if ink else 'aktuelle Tinte'
            days = load.days_loaded
            res = QMessageBox.question(self, t('ui.pen_widget.als_gereinigt_markieren_b5603f6f'), t('ui.pen_widget.mark_cleaned_question', pen=f'{pen.brand} {pen.model}', ink=ink_name, days=days), QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
            if res != QMessageBox.StandardButton.Yes:
                return
            db_load = session.get(InkLoad, load.id)
            if db_load:
                db_load.cleaned_date = datetime.now()
                session.commit()
                AppEventBus.instance().pens_changed.emit()
                self.refresh()
                self._show_details(pen_id)
        finally:
            session.close()

    def _service_block(self):
        pen_id = self._selected_id()
        if not pen_id:
            return
        dlg = ServiceBlockDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        data = dlg.get_data()
        session = get_session()
        try:
            pen = session.get(Pen, pen_id)
            if not pen:
                return
            pen.availability_status = data['status']
            pen.rotation_blocked = True
            pen.service_start_date = data['start']
            pen.service_days = data['days']
            pen.blocked_until = data.get('end')
            pen.service_cost = data['cost'] or None
            pen.service_currency = data.get('currency') or LocaleService.instance().currency
            pen.service_notes = data['notes']
            for load in pen.ink_loads:
                if load.cleaned_date is None:
                    load.cleaned_date = datetime.now()
            if data['cost']:
                session.add(Expense(item_type='service', pen_id=pen.id, amount=data['cost'], shipping=0.0, customs=0.0, currency=pen.service_currency or LocaleService.instance().currency, purchase_date=data['start'], description=f'Service: {pen.brand} {pen.model}', notes=data['notes']))
            session.commit()
            sync_default_outbox_from_session_safely(session)
            AppEventBus.instance().pens_changed.emit()
            AppEventBus.instance().expenses_changed.emit()
            self.refresh()
            self._show_details(pen_id)
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, t('ui.pen_widget.fehler_46938af3'), str(e))
        finally:
            session.close()

    @staticmethod
    def _sync_pen_nib_setup(session, pen: Pen, dlg) -> None:
        """Synchronisiert die neue Setup-Ebene für Feder im konkreten Füller.

        Pen.nib_id bleibt als schnelle Hauptzuweisung erhalten. Zusätzlich gibt
        es genau ein aktives PenNibSetup, das Feed/Flow/Feel im konkreten Füller
        speichert. Ändert sich die Feder, wird das alte Setup historisiert.
        """
        setup_data = dlg.get_nib_setup_data() if hasattr(dlg, 'get_nib_setup_data') else {}
        nib_id = getattr(pen, 'nib_id', None)
        active = None
        for setup in list(getattr(pen, 'nib_setups', []) or []):
            if setup.is_active and setup.removed_date is None:
                active = setup
                break
        if not nib_id:
            if active is not None:
                active.is_active = False
                active.removed_date = datetime.now()
            return
        if active is not None and active.nib_id == nib_id:
            for k, v in setup_data.items():
                setattr(active, k, v)
            active.updated_at = datetime.now()
            return
        if active is not None:
            active.is_active = False
            active.removed_date = datetime.now()
        setup = PenNibSetup(pen_id=pen.id, nib_id=nib_id, **setup_data)
        session.add(setup)

    @staticmethod
    def _norm_text(value) -> str:
        return (value or '').strip().lower().replace('no.', '#').replace('no ', '#').replace('nr.', '#')

    @staticmethod
    def _resolve_nib(session, dlg, current_nib_id=None):
        """Findet/erzeugt ein Feder-Exemplar und dedupliziert das Format.

        v0.2.35:
        - Format wird normalisiert wiederverwendet (Bock/#6/Standard).
        - Exemplar wird NICHT blind zusammengeführt.
        - Wenn aber ein wirklich sehr ähnliches Exemplar existiert, fragt die App:
          vorhandenes verwenden oder neues Exemplar anlegen.
        """
        nib_data = dlg.get_inline_nib_data()
        fmt_mfr = nib_data.pop('_format_manufacturer', None)
        fmt_phys = nib_data.pop('_format_physical_size', None)
        fmt_prop = bool(nib_data.pop('_format_is_proprietary', False))
        fmt_id = find_or_create_nib_format(session, fmt_mfr, fmt_phys, fmt_prop)
        nib_data['format_id'] = fmt_id
        existing = find_similar_nib(session, fmt_id, nib_data)
        if existing is not None:
            answer = QMessageBox.question(dlg, t('ui.pen_widget.ahnliche_feder_gefunden_82364b39'), t('ui.pen_widget.similar_nib_question', label=existing.display_label), QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes)
            if answer == QMessageBox.StandardButton.Yes:
                return existing.id
        nib = Nib(**nib_data)
        session.add(nib)
        session.flush()
        return nib.id

    def _unblock_pen(self):
        pen_id = self._selected_id()
        if not pen_id:
            return
        session = get_session()
        try:
            pen = session.get(Pen, pen_id)
            if pen:
                pen.availability_status = 'available'
                pen.rotation_blocked = False
                pen.blocked_until = None
                pen.service_start_date = None
                pen.service_days = None
                pen.service_cost = None
                pen.service_currency = None
                pen.service_notes = None
                session.commit()
                AppEventBus.instance().pens_changed.emit()
                self.refresh()
                self._show_details(pen_id)
        finally:
            session.close()

    def _toggle_archive_pen(self):
        """Füller archivieren (is_active=False) oder wiederherstellen (is_active=True)."""
        pen_id = self._selected_id()
        if not pen_id:
            return
        session = get_session()
        try:
            pen = session.get(Pen, pen_id)
            if not pen:
                return
            new_state = not pen.is_active
            action_lbl = t('ui.pen_widget.archive_action_restore') if new_state else t('ui.pen_widget.archive_action_archive')
            state_lbl = t('ui.pen_widget.archive_state_active') if new_state else t('ui.pen_widget.archive_state_archived')
            detail_lbl = t('ui.pen_widget.archive_detail_active') if new_state else t('ui.pen_widget.archive_detail_archived')
            res = QMessageBox.question(self, t('ui.pen_widget.archive_title', action=action_lbl), t('ui.pen_widget.archive_message', pen=f'{pen.brand} {pen.model}', state=state_lbl, detail=detail_lbl), QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if res != QMessageBox.StandardButton.Yes:
                return
            pen.is_active = new_state
            if not new_state:
                for load in pen.ink_loads:
                    if load.cleaned_date is None:
                        load.cleaned_date = datetime.now()
                pen.rotation_blocked = True
            else:
                pen.rotation_blocked = False
                pen.availability_status = 'available'
            session.commit()
            AppEventBus.instance().pens_changed.emit()
            self.refresh()
            self._clear_details()
        finally:
            session.close()

    def _clear_details(self):
        while self._detail_body_layout.count():
            item = self._detail_body_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        ph = QLabel(t('ui.pen_widget.wahle_einen_fuller_aus_der_liste_b81e86ba'))
        ph.setStyleSheet('color:#5f6f72;font-size:13px;')
        ph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._detail_body_layout.addWidget(ph)
        self._detail_body_layout.addStretch()
        self._detail_title.setText(t('ui.pen_widget.fuller_auswahlen_9bdd7270'))
        for b in (self.edit_btn, self.del_btn, self.load_btn, self.clean_btn, self.service_btn):
            b.setEnabled(False)

def _sync_purchase_expense_for_pen(session, pen: Pen):
    """Delegiert an logic.pen_service (v0.3.02); Signatur bleibt stabil."""
    sync_purchase_expense_for_pen(session, pen)


# v0.3.02: Dialoge liegen in ui/pen_dialogs (Re-Export für bestehende
# Importe wie `from ui.pen_widget import PenDialog`).
from ui.pen_dialogs import (  # noqa: F401
    LoadInkDialog, PenDialog, ServiceBlockDialog, ServiceHelpDialog,
    SizeCompareDialog,
)
