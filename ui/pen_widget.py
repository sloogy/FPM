"""
Füllerverwaltung – CRUD, Tinte einfüllen, Reinigung markieren, Details-Panel.
"""
from datetime import datetime
import csv
from typing import Optional
from pathlib import Path
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit, QDialog, QFormLayout, QComboBox, QDateEdit, QTextEdit, QCheckBox, QGroupBox, QScrollArea, QMessageBox, QSplitter, QFrame, QSpinBox, QMenu, QTabWidget, QFileDialog, QInputDialog
from PySide6.QtCore import Qt, QDate, QRectF, QPointF
from PySide6.QtGui import QColor, QFont, QPixmap, QPainter, QPen, QBrush, QPolygonF
from database.db import get_session, _data_dir
from i18n.translator import format_money, format_date, LocaleService, normalize_currency_code, t
from i18n.qt_i18n import translate_source_text
from database.models import Pen, Ink, InkLoad, Nib, NibFormat, PenNibSetup, Expense
from logic.rule_engine import RuleEngine, LEVEL_ICONS
from logic.event_bus import AppEventBus
from logic.budget_export_service import sync_default_outbox_from_session
from logic.rotation_engine import RotationEngine
from logic.media_storage_service import import_pen_image
from ui.locale_widgets import (
    LocalizedDoubleSpinBox as QDoubleSpinBox,
    bind_currency_combo,
    current_currency,
    populate_currency_combo,
    set_combo_currency,
)
from ui.ui_scale import scale_px
from ui.ink_widget import InkDialog
from ui.nib_widget import NibDialog
from ui.role_prefs_dialog import RolePrefsDialog
from ui.theme import BTN_ACCENT, BTN_MUTED, BTN_PRIMARY, BTN_SECONDARY, BTN_SUCCESS
FILL_SYSTEM_KEYS = ['piston', 'vac', 'converter', 'cartridge', 'eyedropper']

def _fill_systems():
    return [(key, t(f'pen.fill_systems.{key}')) for key in FILL_SYSTEM_KEYS]

def _fill_system_label(key: str | None) -> str:
    return dict(_fill_systems()).get(key, key or '')
TAG_KEYS = ['grail', 'problem', 'collector', 'vintage']

def _tag_label(key: str) -> str:
    return t(f'pen.tags_list.{key}') if key else ''

def _rotation_roles():
    return [('writer', t('rotation.role_writer')), ('edc', t('rotation.role_edc')), ('agenda', t('rotation.role_agenda')), ('journal', t('rotation.role_journal')), ('work', t('rotation.role_work')), ('creative', t('rotation.role_creative')), ('letter', t('rotation.role_letter')), ('collector', t('rotation.role_collector')), ('vintage', t('rotation.role_vintage')), ('problem', t('rotation.role_problem')), ('fine', t('rotation.role_fine')), ('broad', t('rotation.role_broad'))]
ROTATION_ROLES = _rotation_roles()

def _rotation_themes():
    return [(None, t('rotation.theme_auto')), ('edc', t('rotation.theme_edc')), ('agenda', t('rotation.theme_agenda')), ('journal', t('rotation.theme_journal')), ('work', t('rotation.theme_work')), ('creative', t('rotation.theme_creative')), ('letter', t('rotation.theme_letter')), ('archive', t('rotation.theme_archive')), ('cheap_paper', t('rotation.theme_cheap')), ('fine_nib', t('rotation.theme_fine_nib')), ('broad_nib', t('rotation.theme_broad_nib')), ('sheen_showcase', t('rotation.theme_sheen')), ('testing', t('rotation.theme_testing'))]
ROTATION_THEMES = _rotation_themes()
BLOCKING_STATUSES = {'problem', 'service', 'blocked', 'dry_risk'}

def _status_label(key: str | None) -> str:
    return t(f'dashboard.status_labels.{key}') if key else ''

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
        add_btn.setStyleSheet(BTN_PRIMARY)
        add_btn.clicked.connect(self._add)
        hdr.addWidget(add_btn)
        import_btn = QPushButton(t('ui.pen_widget.import_e7ffd6f8'))
        import_btn.setStyleSheet('background:#7f8c8d;color:white;border:none;padding:7px 14px;border-radius:5px;font-weight:bold;')
        import_btn.clicked.connect(self._import_pens)
        hdr.addWidget(import_btn)
        copy_btn = QPushButton(t('ui.pen_widget.fuller_kopieren_0fb5ffd0'))
        copy_btn.setStyleSheet(BTN_ACCENT)
        copy_btn.clicked.connect(self._copy_pen)
        hdr.addWidget(copy_btn)
        help_btn = QPushButton(t('ui.pen_widget.service_hilfe_26a2c650'))
        help_btn.setStyleSheet(BTN_ACCENT)
        help_btn.clicked.connect(self._show_service_help)
        hdr.addWidget(help_btn)
        size_btn = QPushButton(t('ui.pen_widget.groenvergleich_4de65487'))
        size_btn.setStyleSheet(BTN_SECONDARY)
        size_btn.clicked.connect(self._show_size_compare)
        hdr.addWidget(size_btn)
        export_btn = QPushButton(t('ui.pen_widget.fuller_exportieren_d7b5b88d'))
        export_btn.setStyleSheet(BTN_SECONDARY)
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
        ph.setStyleSheet('color:#95a5a6;font-size:13px;')
        ph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._detail_body_layout.addWidget(ph)
        self._detail_body_layout.addStretch()
        return panel

    def refresh(self):
        session = get_session()
        try:
            show_archived = getattr(self, '_show_archived_cb', None) and self._show_archived_cb.isChecked()
            if show_archived:
                pens = session.query(Pen).order_by(Pen.brand, Pen.model).all()
            else:
                pens = session.query(Pen).filter_by(is_active=True).order_by(Pen.brand, Pen.model).all()
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
                status_item.setForeground(QColor('#8e44ad' if status_txt.startswith('🔒') else '#27ae60' if pen.current_ink_load else '#7f8c8d'))
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
                lbl.setStyleSheet('color:#7f8c8d; min-width:150px;')
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
                row(t('ui.pen_widget.feder_82b25afd'), t('ui.pen_widget.legacy_exact.text_012'), '#95a5a6')
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
                row(t('ui.pen_widget.legacy_exact.text_025'), t('pen.no_ink'), '#95a5a6')
            self._add_enthusiast_actions(pen.id)
            for note_label, note_text, nc in ((t('pen.writing_feel'), pen.writing_feel_notes, '#2c3e50'), ('⚠ ' + t('pen.problems'), pen.problem_notes, '#e74c3c'), (t('pen.cleaning'), pen.cleaning_notes, '#7f8c8d')):
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
        from database.models import WritingSample, Paper
        from logic.writing_sample_service import compare_samples
        from ui.writing_samples_widget import WritingSampleComparisonDialog
        session = get_session()
        try:
            samples = (
                session.query(WritingSample)
                .filter(WritingSample.pen_id == pen_id)
                .order_by(WritingSample.written_at.desc(), WritingSample.id.desc())
                .all()
            )
            if len(samples) < 2:
                QMessageBox.information(self, t("writing_samples.compare_title"), t("pen_detail.sample_need_two_for_pen"))
                return
            pens = {p.id: p for p in session.query(Pen).all()}
            inks = {i.id: i for i in session.query(Ink).all()}
            papers = {p.id: p for p in session.query(Paper).all()}
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
            setups = (
                session.query(PenNibSetup)
                .filter(PenNibSetup.pen_id == pen_id)
                .order_by(PenNibSetup.installed_date.desc())
                .all()
            )
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
        expenses = session.query(Expense).filter(Expense.pen_id == pen_id).order_by(Expense.purchase_date.desc().nullslast(), Expense.id.desc()).all()
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet('color:#eee; margin:10px 0;')
        self._detail_body_layout.addWidget(sep)
        title = QLabel(t('ui.pen_widget.buchungshistorie_65d20c39'))
        title.setStyleSheet('font-size:14px;color:#1e2a38;padding-top:4px;')
        self._detail_body_layout.addWidget(title)
        if not expenses:
            empty = QLabel(t('ui.pen_widget.noch_keine_ausgaben_buchungen_mit_diesem_fuller__a011fee5'))
            empty.setStyleSheet('color:#95a5a6;font-size:12px;')
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
            currency = exp.currency or LocaleService.instance().currency
            total = exp.total or 0.0
            total_by_currency[currency] = total_by_currency.get(currency, 0.0) + total
            values = [
                date_txt,
                typ_txt,
                desc_txt,
                format_money(exp.amount or 0.0, currency),
                format_money(total, currency),
            ]
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
        totals = ' · '.join(
            format_money(amount, cur)
            for cur, amount in sorted(total_by_currency.items())
        )
        total_lbl = QLabel(t('ui.pen_widget.total_bookings_sum', total=totals))
        total_lbl.setStyleSheet('color:#2c3e50;font-weight:bold;padding:4px 0;')
        self._detail_body_layout.addWidget(total_lbl)

    def _export_pens(self):
        path, _ = QFileDialog.getSaveFileName(self, t('ui.pen_widget.fuller_kenndaten_exportieren_ea57a5a0'), 'fueller_export.csv', t('ui.pen_widget.csv_dateien_csv_a2c5e427'))
        if not path:
            return
        session = get_session()
        try:
            pens = session.query(Pen).order_by(Pen.brand, Pen.model).all()
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
            sync_default_outbox_from_session(session)
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
        """Import an image without risking the pen transaction."""
        self._last_media_warning = None
        raw = getattr(pen, 'image_path', None)
        if not raw:
            return
        try:
            imported = import_pen_image(
                _data_dir(),
                raw,
                pen_id=pen.id,
                brand=pen.brand,
                model=pen.model,
            )
        except Exception as exc:  # media is optional; the pen itself must survive
            self._last_media_warning = str(exc)
            return
        if imported:
            pen.image_path = imported

    def _warn_media_import_failed(self) -> None:
        message = getattr(self, '_last_media_warning', None)
        if not message:
            return
        self._last_media_warning = None
        QMessageBox.warning(
            self,
            t('media.import_failed_title'),
            t('media.import_failed_body', error=message),
        )

    def _add(self) -> bool:
        dlg = PenDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return False
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
            return True
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, t('ui.pen_widget.fehler_46938af3'), str(e))
            return False
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
            if not str(v or '').strip():
                return None
            return LocaleService.instance().parse_number(str(v))

        def to_int(v, default=None):
            value = to_float(v)
            return int(value) if value is not None else default

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
                        pen = session.query(Pen).filter(Pen.brand == brand, Pen.model == model, Pen.color == color, Pen.ink_capacity_ml == capacity).first()
                        data = dict(brand=brand, model=model, color=color, ink_capacity_ml=capacity, fill_system=(row.get('fill_system') or row.get('Füllsystem') or 'converter').strip() or 'converter', purchase_price=to_float(row.get('purchase_price') or row.get('Kaufpreis')), purchase_currency=normalize_currency_code(row.get('purchase_currency') or row.get('Kaufpreis-Währung'), LocaleService.instance().currency), current_market_value=to_float(row.get('current_market_value') or row.get('Marktwert')), market_currency=normalize_currency_code(row.get('market_currency') or row.get('Marktwert-Währung') or row.get('purchase_currency'), LocaleService.instance().currency), insurance_value=to_float(row.get('insurance_value') or row.get('Versicherungswert')), insurance_currency=normalize_currency_code(row.get('insurance_currency') or row.get('Versicherungswert-Währung'), LocaleService.instance().currency), length_mm=to_float(row.get('length_mm') or row.get('Länge geschlossen')), length_uncapped_mm=to_float(row.get('length_uncapped_mm') or row.get('Länge offen')), length_posted_mm=to_float(row.get('length_posted_mm') or row.get('Länge gepostet')), diameter_mm=to_float(row.get('diameter_mm') or row.get('Durchmesser')), section_diameter_mm=to_float(row.get('section_diameter_mm') or row.get('Griffdurchmesser')), weight_g=to_float(row.get('weight_g') or row.get('Gewicht')), popularity_rating=to_int(row.get('popularity_rating') or row.get('Beliebtheit'), 3), rotation_role=(row.get('rotation_role') or row.get('Rotationsrolle') or 'writer').strip() or 'writer', rotation_theme=(row.get('rotation_theme') or row.get('Standard-Thema') or row.get('Thema') or '').strip() or None, tags=(row.get('tags') or row.get('Tags') or '').strip() or None, writing_feel_notes=(row.get('writing_feel_notes') or row.get('Schreibgefühl') or '').strip() or None, problem_notes=(row.get('problem_notes') or row.get('Probleme') or '').strip() or None, cleaning_notes=(row.get('cleaning_notes') or row.get('Reinigung') or '').strip() or None, purchase_date=to_date(row.get('purchase_date') or row.get('Kaufdatum')))
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
            dup = session.query(Pen).filter(Pen.brand == data.get('brand'), Pen.model == data.get('model'), Pen.color == data.get('color'), Pen.ink_capacity_ml == data.get('ink_capacity_ml'), Pen.is_active == True).first()
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
            active = session.query(Pen).filter_by(is_active=True).all()
        finally:
            session.close()
        if len(active) == 1:
            return active[0].id
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
            sync_default_outbox_from_session(session)
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
        norm_mfr = PenWidget._norm_text(fmt_mfr)
        norm_phys = PenWidget._norm_text(fmt_phys)
        fmt_id = None
        if fmt_mfr or fmt_phys:
            existing_fmt = None
            for fmt in session.query(NibFormat).all():
                if PenWidget._norm_text(fmt.manufacturer) == norm_mfr and PenWidget._norm_text(fmt.physical_size) == norm_phys and (bool(fmt.is_proprietary) == fmt_prop):
                    existing_fmt = fmt
                    break
            if existing_fmt:
                fmt_id = existing_fmt.id
            else:
                fmt = NibFormat(manufacturer=(fmt_mfr or 'Unbekannt').strip(), physical_size=(fmt_phys or '').strip() or None, is_proprietary=fmt_prop)
                session.add(fmt)
                session.flush()
                fmt_id = fmt.id
        nib_data['format_id'] = fmt_id
        candidates = session.query(Nib).filter(Nib.format_id == fmt_id).all() if fmt_id else []
        for existing in candidates:
            same = PenWidget._norm_text(existing.size) == PenWidget._norm_text(nib_data.get('size')) and PenWidget._norm_text(existing.material) == PenWidget._norm_text(nib_data.get('material')) and (PenWidget._norm_text(existing.grind) == PenWidget._norm_text(nib_data.get('grind'))) and (PenWidget._norm_text(existing.source) == PenWidget._norm_text(nib_data.get('source'))) and (bool(existing.is_proprietary) == bool(nib_data.get('is_proprietary')))
            if same:
                answer = QMessageBox.question(dlg, t('ui.pen_widget.ahnliche_feder_gefunden_82364b39'), t('ui.pen_widget.similar_nib_question', label=existing.display_label), QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes)
                if answer == QMessageBox.StandardButton.Yes:
                    return existing.id
                break
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
        ph.setStyleSheet('color:#95a5a6;font-size:13px;')
        ph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._detail_body_layout.addWidget(ph)
        self._detail_body_layout.addStretch()
        self._detail_title.setText(t('ui.pen_widget.fuller_auswahlen_9bdd7270'))
        for b in (self.edit_btn, self.del_btn, self.load_btn, self.clean_btn, self.service_btn):
            b.setEnabled(False)

def _sync_purchase_expense_for_pen(session, pen: Pen):
    """Füller-Kaufpreis als Ausgaben-Tracker-Eintrag spiegeln.

    Die App hält genau einen automatisch erzeugten Kauf-Eintrag je Füller aktuell.
    Manuelle Ausgaben können zusätzlich im Ausgaben-Tracker ergänzt werden.
    """
    if not pen or not pen.id:
        return
    auto_tag = f'AUTO-PEN-PURCHASE:{pen.id}'
    exp = session.query(Expense).filter(Expense.pen_id == pen.id, Expense.notes == auto_tag, Expense.item_type == 'pen').first()
    price = pen.purchase_price or 0.0
    if price <= 0:
        if exp:
            session.delete(exp)
        return
    if not exp:
        exp = Expense(item_type='pen', pen_id=pen.id, shipping=0.0, customs=0.0, currency=getattr(pen, 'purchase_currency', None) or LocaleService.instance().currency, notes=auto_tag)
        session.add(exp)
    exp.amount = price
    exp.currency = getattr(pen, 'purchase_currency', None) or LocaleService.instance().currency
    exp.purchase_date = pen.purchase_date
    exp.description = f'Kauf: {pen.brand} {pen.model}'
SERVICE_HELP = {'de': {'piston': 'Kolbenfüller: Vor Service entleeren, mit lauwarmem Wasser spülen. Keine Gewalt am Kolbenknopf. Bei schwergängigem Kolben: nicht weiterdrehen, Service eintragen.', 'vac': 'Vac-Füller: Keine Shimmer-/Pigmenttinte für lange Standzeiten. Mehrfach spülen, Dichtung prüfen. Bei kratzigem Hub oder Leck: sperren und Service planen.', 'converter': 'Converter: Converter herausnehmen, separat spülen. Ideal für schnelle Reinigung und Tintenwechsel. Defekte Converter können günstig ersetzt werden.', 'cartridge': 'Patrone: Patrone entfernen, Griffstück spülen. Alte Patronen nicht lange offen lagern. Bei Startproblemen Feed wässern.', 'eyedropper': 'Eyedropper: Vor dem Öffnen vollständig entleeren. Gewinde/Dichtung prüfen und vorsichtig fetten. Shimmer kann sedimentieren – regelmäßig bewegen und reinigen.'}, 'en': {'piston': 'Piston filler: empty before service and flush with lukewarm water. Do not force the piston knob. If it feels stuck, block the pen and schedule service.', 'vac': 'Vac filler: avoid shimmer/pigment inks for long rotations. Flush thoroughly and check seals. Block the pen if the plunger feels rough or leaks.', 'converter': 'Converter: remove and flush separately. Best for easy cleaning and frequent ink changes. Faulty converters are usually easy to replace.', 'cartridge': 'Cartridge: remove cartridge and flush the section. Do not store opened cartridges for too long. Soak the feed if the pen has hard starts.', 'eyedropper': 'Eyedropper: empty fully before opening. Check seals/threads and grease carefully. Shimmer may settle, so move and clean regularly.'}, 'fr': {'piston': 'Stylo à piston : vider avant service et rincer à l’eau tiède. Ne pas forcer le bouton du piston. Si le mécanisme bloque, mettre le stylo en service.', 'vac': 'Vac filler : éviter les encres shimmer/pigmentées en longue rotation. Rincer soigneusement et contrôler les joints. Bloquer en cas de fuite ou de piston rugueux.', 'converter': 'Convertisseur : retirer et rincer séparément. Très pratique pour les changements d’encre. Un convertisseur défectueux se remplace facilement.', 'cartridge': 'Cartouche : retirer la cartouche et rincer la section. Ne pas garder les cartouches ouvertes trop longtemps. Tremper le feed en cas de démarrage difficile.', 'eyedropper': 'Eyedropper : vider complètement avant ouverture. Vérifier les joints/filetages et graisser prudemment. Le shimmer peut se déposer : nettoyer régulièrement.'}}

class ServiceHelpDialog(QDialog):

    def __init__(self, parent=None, fill_system: Optional[str]=None):
        super().__init__(parent)
        self.setWindowTitle(t('ui.pen_widget.service_hilfe_fd1578b6'))
        self.setMinimumSize(620, 420)
        root = QVBoxLayout(self)
        controls = QHBoxLayout()
        self.lang_combo = QComboBox()
        self.lang_combo.addItem(t('ui.pen_widget.deutsch_19e623b9'), 'de')
        self.lang_combo.addItem(t('ui.pen_widget.english_edb0886e'), 'en')
        self.lang_combo.addItem(t('ui.pen_widget.francais_a0642c90'), 'fr')
        self.fs_combo = QComboBox()
        for val, lbl in _fill_systems():
            self.fs_combo.addItem(lbl, val)
        if fill_system:
            idx = self.fs_combo.findData(fill_system)
            if idx >= 0:
                self.fs_combo.setCurrentIndex(idx)
        controls.addWidget(QLabel(t('ui.pen_widget.sprache_a988b2b3')))
        controls.addWidget(self.lang_combo)
        controls.addWidget(QLabel(t('ui.pen_widget.fullsystem_27f68a34')))
        controls.addWidget(self.fs_combo, 1)
        root.addLayout(controls)
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setStyleSheet('font-size:14px; line-height:1.35; background:#f8fafc;')
        root.addWidget(self.text, 1)
        self.lang_combo.currentIndexChanged.connect(self._refresh)
        self.fs_combo.currentIndexChanged.connect(self._refresh)
        self._refresh()
        br = QHBoxLayout()
        br.addStretch()
        close = QPushButton(t('ui.pen_widget.schlieen_0d07871e'))
        close.clicked.connect(self.accept)
        br.addWidget(close)
        root.addLayout(br)

    def _refresh(self):
        lang = self.lang_combo.currentData()
        fs = self.fs_combo.currentData()
        title = self.fs_combo.currentText()
        body = SERVICE_HELP.get(lang, SERVICE_HELP['de']).get(fs, '')
        footer = t('ui.pen_widget.service_help_footer')
        self.text.setHtml(f'<h2>{title}</h2><p>{body}</p><hr><p>{footer}</p>')

class SizeCompareDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t('ui.pen_widget.groenvergleich_597a816d'))
        self.setMinimumSize(980, 680)
        root = QVBoxLayout(self)
        hint = QLabel(t('ui.pen_widget.size_compare_visual_hint'))
        hint.setWordWrap(True)
        hint.setStyleSheet('color:#566573;')
        root.addWidget(hint)

        controls = QHBoxLayout()
        controls.addWidget(QLabel(t('ui.pen_widget.size_compare_mode_label')))
        self.mode_combo = QComboBox()
        self.mode_combo.addItem(t('ui.pen_widget.size_compare_mode_overlay'), 'overlay')
        self.mode_combo.addItem(t('ui.pen_widget.size_compare_mode_rows'), 'rows')
        controls.addWidget(self.mode_combo)
        controls.addSpacing(18)
        controls.addWidget(QLabel(t('ui.pen_widget.size_compare_metric_label')))
        self.metric_combo = QComboBox()
        self.metric_combo.addItem(t('ui.pen_widget.size_compare_metric_best'), 'best')
        self.metric_combo.addItem(t('ui.pen_widget.size_compare_metric_closed'), 'closed')
        self.metric_combo.addItem(t('ui.pen_widget.size_compare_metric_uncapped'), 'uncapped')
        self.metric_combo.addItem(t('ui.pen_widget.size_compare_metric_posted'), 'posted')
        controls.addWidget(self.metric_combo)
        controls.addStretch(1)
        root.addLayout(controls)

        self.image = QLabel()
        self.image.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.image)
        root.addWidget(scroll, 1)
        self.mode_combo.currentIndexChanged.connect(self._draw)
        self.metric_combo.currentIndexChanged.connect(self._draw)
        self._draw()
        br = QHBoxLayout()
        br.addStretch()
        close = QPushButton(t('ui.pen_widget.schlieen_0d07871e'))
        close.clicked.connect(self.accept)
        br.addWidget(close)
        root.addLayout(br)

    @staticmethod
    def _display_value(value) -> float:
        try:
            number = float(value or 0)
        except (TypeError, ValueError):
            return 0.0
        return number if number > 0 else 0.0

    def _collect_rows(self):
        session = get_session()
        try:
            pens = session.query(Pen).order_by(Pen.brand, Pen.model).all()
            rows = []
            for p in pens:
                closed = self._display_value(getattr(p, 'length_mm', None))
                uncapped = self._display_value(getattr(p, 'length_uncapped_mm', None))
                posted = self._display_value(getattr(p, 'length_posted_mm', None))
                if max(closed, uncapped, posted) <= 0:
                    continue
                rows.append({
                    'name': f'{p.brand or ""} {p.model or ""}'.strip() or t('ui.pen_widget.fuller_e5df3d89'),
                    'closed': closed,
                    'uncapped': uncapped,
                    'posted': posted,
                    'weight': self._display_value(getattr(p, 'weight_g', None)),
                    'diameter': self._display_value(getattr(p, 'diameter_mm', None)),
                })
            return rows
        finally:
            session.close()

    def _metric_label(self, metric: str) -> str:
        return {
            'closed': t('ui.pen_widget.size_compare_metric_closed'),
            'uncapped': t('ui.pen_widget.size_compare_metric_uncapped'),
            'posted': t('ui.pen_widget.size_compare_metric_posted'),
            'best': t('ui.pen_widget.size_compare_metric_best'),
        }.get(metric, metric)

    def _row_length(self, row: dict) -> tuple[float, str]:
        metric = self.metric_combo.currentData() if hasattr(self, 'metric_combo') else 'best'
        if metric in ('closed', 'uncapped', 'posted') and row.get(metric, 0) > 0:
            return float(row[metric]), metric
        if metric in ('closed', 'uncapped', 'posted'):
            # Fallback statt leerer Darstellung: der Füller bleibt vergleichbar.
            for key in ('closed', 'uncapped', 'posted'):
                if row.get(key, 0) > 0:
                    return float(row[key]), key
        for key in ('posted', 'closed', 'uncapped'):
            if row.get(key, 0) > 0:
                return float(row[key]), key
        return 0.0, 'closed'

    def _color_for_index(self, index: int, alpha: int = 210) -> QColor:
        palette = ['#2563eb', '#16a34a', '#dc2626', '#9333ea', '#0891b2', '#ca8a04', '#475569', '#be185d']
        color = QColor(palette[index % len(palette)])
        color.setAlpha(alpha)
        return color

    def _draw_ruler(self, painter: QPainter, left: int, right: int, y: int, max_len: float, scale: float):
        painter.setPen(QPen(QColor('#cbd5e1'), 1))
        painter.drawLine(left, y, right, y)
        if max_len <= 0:
            return
        step = 25 if max_len <= 180 else 50
        current = step
        painter.setFont(QFont('', 8))
        while current <= max_len + step:
            x = left + int(current * scale)
            if x > right:
                break
            painter.drawLine(x, y - 5, x, y + 5)
            painter.setPen(QPen(QColor('#64748b'), 1))
            painter.drawText(x - 14, y - 8, f'{current:g}')
            painter.setPen(QPen(QColor('#cbd5e1'), 1))
            current += step

    def _draw_pen_silhouette(
        self,
        painter: QPainter,
        x: int,
        center_y: int,
        length_px: int,
        thickness_px: int,
        color: QColor,
        metric: str,
        *,
        label: str | None = None,
    ):
        length_px = max(70, int(length_px))
        thickness_px = max(14, min(28, int(thickness_px)))
        y = int(center_y - thickness_px / 2)
        body_color = QColor(color)
        body_color.setAlpha(max(70, color.alpha()))
        dark = QColor(body_color).darker(125)
        light = QColor(body_color).lighter(155)

        painter.setPen(QPen(QColor('#1f2937'), 1))
        painter.setBrush(QBrush(body_color))

        if metric == 'uncapped':
            nib_len = max(24, int(length_px * 0.16))
            section_len = max(16, int(length_px * 0.10))
            barrel_len = max(36, length_px - nib_len - section_len)
            painter.drawRoundedRect(QRectF(x, y, barrel_len, thickness_px), thickness_px / 2, thickness_px / 2)
            painter.setBrush(QBrush(light))
            painter.drawRoundedRect(QRectF(x + barrel_len - 6, y + 2, section_len + 8, thickness_px - 4), 6, 6)
            nib = QPolygonF([
                QPointF(x + barrel_len + section_len, y + 2),
                QPointF(x + barrel_len + section_len + nib_len, center_y),
                QPointF(x + barrel_len + section_len, y + thickness_px - 2),
            ])
            painter.setBrush(QBrush(QColor('#e5e7eb')))
            painter.drawPolygon(nib)
            painter.drawLine(x + barrel_len + section_len + 4, center_y, x + barrel_len + section_len + nib_len - 5, center_y)
        elif metric == 'posted':
            cap_len = max(38, int(length_px * 0.28))
            nib_len = max(22, int(length_px * 0.13))
            section_len = max(14, int(length_px * 0.08))
            barrel_len = max(44, length_px - nib_len - section_len)
            painter.setBrush(QBrush(light))
            painter.drawRoundedRect(QRectF(x, y + 2, cap_len, thickness_px - 4), thickness_px / 2, thickness_px / 2)
            painter.setBrush(QBrush(body_color))
            painter.drawRoundedRect(QRectF(x + cap_len * 0.55, y, barrel_len - cap_len * 0.10, thickness_px), thickness_px / 2, thickness_px / 2)
            painter.setBrush(QBrush(light))
            sx = x + barrel_len - 4
            painter.drawRoundedRect(QRectF(sx, y + 2, section_len + 8, thickness_px - 4), 6, 6)
            nib = QPolygonF([
                QPointF(sx + section_len, y + 2),
                QPointF(x + length_px, center_y),
                QPointF(sx + section_len, y + thickness_px - 2),
            ])
            painter.setBrush(QBrush(QColor('#e5e7eb')))
            painter.drawPolygon(nib)
            painter.setPen(QPen(dark, 1))
            painter.drawLine(x + cap_len, y + 4, x + cap_len, y + thickness_px - 4)
        else:
            cap_len = max(38, int(length_px * 0.38))
            painter.drawRoundedRect(QRectF(x, y, length_px, thickness_px), thickness_px / 2, thickness_px / 2)
            painter.setPen(QPen(dark, 1))
            painter.drawLine(x + cap_len, y + 3, x + cap_len, y + thickness_px - 3)
            painter.setPen(QPen(QColor('#f8fafc'), 2))
            clip_x = x + max(12, int(cap_len * 0.22))
            painter.drawLine(clip_x, y + 4, clip_x + int(cap_len * 0.44), y + 4)
            painter.drawLine(clip_x + int(cap_len * 0.44), y + 4, clip_x + int(cap_len * 0.50), y + thickness_px - 4)

        if label:
            painter.setPen(QPen(QColor('#334155'), 1))
            painter.setFont(QFont('', 9))
            painter.drawText(x + length_px + 10, center_y + 4, label)

    def _draw_overlay(self, painter: QPainter, rows: list[dict], width: int, height: int):
        left = 155
        right = width - 95
        usable = right - left
        lengths = [self._row_length(row)[0] for row in rows]
        max_len = max(lengths) if lengths else 1
        scale = usable / max_len
        painter.setFont(QFont('', 12, QFont.Weight.Bold))
        painter.setPen(QPen(QColor('#0f172a')))
        painter.drawText(20, 34, t('ui.pen_widget.size_compare_overlay_title'))
        painter.setFont(QFont('', 9))
        painter.setPen(QPen(QColor('#64748b')))
        painter.drawText(left, 34, t('ui.pen_widget.size_compare_ruler_mm'))
        self._draw_ruler(painter, left, right, 58, max_len, scale)

        row_gap = min(34, max(22, int((height - 120) / max(1, len(rows)))))
        start_y = 100
        for i, row in enumerate(rows):
            length, metric = self._row_length(row)
            y = start_y + i * row_gap
            color = self._color_for_index(i, 150)
            thickness = row.get('diameter') or 14
            label = f"{row['name'][:30]} · {length:g} mm · {self._metric_label(metric)}"
            self._draw_pen_silhouette(
                painter,
                left,
                y,
                int(length * scale),
                int(max(15, min(28, thickness * 1.35))),
                color,
                metric,
                label=label,
            )
        painter.setPen(QPen(QColor('#94a3b8'), 1))
        painter.drawLine(left, start_y + len(rows) * row_gap + 10, left, max(70, start_y - 30))

    def _draw_rows(self, painter: QPainter, rows: list[dict], width: int, height: int):
        left = 245
        right = width - 105
        usable = right - left
        lengths = [self._row_length(row)[0] for row in rows]
        max_len = max(lengths) if lengths else 1
        scale = usable / max_len
        painter.setFont(QFont('', 10, QFont.Weight.Bold))
        painter.setPen(QPen(QColor('#0f172a')))
        painter.drawText(22, 34, t('ui.pen_widget.size_chart_title'))
        painter.drawText(left, 34, t('ui.pen_widget.size_compare_scaled_title'))
        self._draw_ruler(painter, left, right, 58, max_len, scale)
        row_h = 74
        for i, row in enumerate(rows):
            y = 95 + i * row_h
            if i % 2:
                painter.fillRect(QRectF(0, y - 32, width, row_h), QBrush(QColor('#f8fafc')))
            length, metric = self._row_length(row)
            painter.setPen(QPen(QColor('#475569')))
            painter.setFont(QFont('', 9))
            painter.drawText(22, y + 5, row['name'][:34])
            sub = f"{length:g} mm · {self._metric_label(metric)}"
            if row.get('weight'):
                sub += f" · {row['weight']:g} g"
            painter.setPen(QPen(QColor('#64748b')))
            painter.drawText(22, y + 24, sub)
            color = self._color_for_index(i, 215)
            thickness = row.get('diameter') or 14
            self._draw_pen_silhouette(
                painter,
                left,
                y + 8,
                int(length * scale),
                int(max(16, min(30, thickness * 1.45))),
                color,
                metric,
                label=f'{length:g} mm',
            )

    def _draw(self):
        rows = self._collect_rows()
        if not rows:
            self.image.setText(t('ui.pen_widget.noch_keine_langen_gespeichert_trage_bei_fullern__548174d0'))
            return
        mode = self.mode_combo.currentData() if hasattr(self, 'mode_combo') else 'overlay'
        if mode == 'rows':
            width = 1120
            height = max(260, 105 + 74 * len(rows))
        else:
            width = 1120
            height = max(360, 145 + min(34, max(22, int(420 / max(1, len(rows))))) * len(rows))
        pix = QPixmap(width, height)
        pix.fill(QColor('#ffffff'))
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(QRectF(0, 0, width, height), QBrush(QColor('#ffffff')))
        if mode == 'rows':
            self._draw_rows(painter, rows, width, height)
        else:
            self._draw_overlay(painter, rows, width, height)
        painter.end()
        self.image.setPixmap(pix)

class ServiceBlockDialog(QDialog):
    """Füller temporär sperren / Service eintragen."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t('ui.pen_widget.fuller_sperren_service_1d2668b1'))
        self.setMinimumWidth(520)
        self._syncing_dates = False
        root = QVBoxLayout(self)
        grp = QGroupBox(t('ui.pen_widget.sperre_service_3b5285a0'))
        fl = QFormLayout(grp)
        self.status_combo = QComboBox()
        self.status_combo.addItem(t('ui.pen_widget.problemfuller_76716b71'), 'problem')
        self.status_combo.addItem(t('ui.pen_widget.in_service_fef475bf'), 'service')
        self.status_combo.addItem(t('ui.pen_widget.austrocknungsrisiko_reinigung_notig_fb89a7ff'), 'dry_risk')
        self.status_combo.addItem(t('ui.pen_widget.sonstige_sperre_6ef7ee3a'), 'blocked')
        self.start_edit = QDateEdit(QDate.currentDate())
        self.start_edit.setCalendarPopup(True)
        self.start_edit.setDisplayFormat(LocaleService.instance().qt_date_format)
        self.days_spin = QSpinBox()
        self.days_spin.setRange(0, 3650)
        self.days_spin.setValue(30)
        self.days_spin.setSuffix(t('ui.pen_widget.tage_18af0ecf'))
        self.end_edit = QDateEdit(QDate.currentDate().addDays(30))
        self.end_edit.setCalendarPopup(True)
        self.end_edit.setDisplayFormat(LocaleService.instance().qt_date_format)
        self.indefinite_cb = QCheckBox(t('ui.pen_widget.ohne_enddatum_manuell_entsperren_680bcd67'))
        self.indefinite_cb.toggled.connect(self._toggle_indefinite)
        self.start_edit.dateChanged.connect(self._sync_end_from_days)
        self.days_spin.valueChanged.connect(self._sync_end_from_days)
        self.end_edit.dateChanged.connect(self._sync_days_from_end)
        self.cost_spin = QDoubleSpinBox()
        self.cost_spin.setRange(0, 99999)
        self.cost_spin.setDecimals(2)
        self.cost_currency_combo = QComboBox()
        populate_currency_combo(self.cost_currency_combo)
        bind_currency_combo(self.cost_currency_combo, self.cost_spin)
        _cost_row = QHBoxLayout()
        _cost_row.addWidget(self.cost_spin, 1)
        _cost_row.addWidget(self.cost_currency_combo)
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(90)
        self.notes_edit.setPlaceholderText(t('ui.pen_widget.z_b_feder_kratzt_kolbenservice_beim_nibmeister_a_f40c70a5'))
        fl.addRow(t('ui.pen_widget.status_f66ce01f'), self.status_combo)
        fl.addRow(t('ui.pen_widget.startdatum_277f917a'), self.start_edit)
        fl.addRow(t('ui.pen_widget.dauer_0c4af07a'), self.days_spin)
        fl.addRow(t('ui.pen_widget.geplantes_ende_e896aa0e'), self.end_edit)
        fl.addRow('', self.indefinite_cb)
        fl.addRow(t('ui.pen_widget.servicekosten_126d7edf'), _cost_row)
        fl.addRow(t('ui.pen_widget.notiz_cb04ac6c'), self.notes_edit)
        root.addWidget(grp)
        hint = QLabel(t('ui.pen_widget.der_fuller_wird_aus_rotation_full_auto_mode_und__02f829a8'))
        hint.setWordWrap(True)
        hint.setStyleSheet('color:#7f8c8d; padding:6px;')
        root.addWidget(hint)
        br = QHBoxLayout()
        br.addStretch()
        cancel = QPushButton(t('ui.pen_widget.abbrechen_bbc8a352'))
        cancel.clicked.connect(self.reject)
        ok = QPushButton(t('ui.pen_widget.sperren_9e9f9a29'))
        ok.setStyleSheet('background:#8e44ad;color:white;border:none;padding:7px 18px;border-radius:5px;font-weight:bold;')
        ok.clicked.connect(self.accept)
        br.addWidget(cancel)
        br.addWidget(ok)
        root.addLayout(br)

    def _toggle_indefinite(self, checked: bool):
        self.days_spin.setEnabled(not checked)
        self.end_edit.setEnabled(not checked)
        if checked:
            self.days_spin.setValue(0)

    def _sync_end_from_days(self, *args):
        if self._syncing_dates or self.indefinite_cb.isChecked():
            return
        self._syncing_dates = True
        self.end_edit.setDate(self.start_edit.date().addDays(self.days_spin.value()))
        self._syncing_dates = False

    def _sync_days_from_end(self, *args):
        if self._syncing_dates or self.indefinite_cb.isChecked():
            return
        self._syncing_dates = True
        days = self.start_edit.date().daysTo(self.end_edit.date())
        self.days_spin.setValue(max(0, days))
        self._syncing_dates = False

    def get_data(self):
        start_qd = self.start_edit.date()
        start = datetime(start_qd.year(), start_qd.month(), start_qd.day())
        end = None
        days = 0
        if not self.indefinite_cb.isChecked():
            end_qd = self.end_edit.date()
            end = datetime(end_qd.year(), end_qd.month(), end_qd.day())
            days = max(0, start_qd.daysTo(end_qd))
        return {'status': self.status_combo.currentData(), 'start': start, 'end': end, 'days': days, 'cost': self.cost_spin.value(), 'currency': current_currency(self.cost_currency_combo), 'notes': self.notes_edit.toPlainText().strip() or None}

class PenDialog(QDialog):
    """Dialog zum Anlegen/Bearbeiten eines Füllers."""

    def __init__(self, parent=None, pen: Optional[Pen]=None):
        super().__init__(parent)
        self.pen = pen
        self.setWindowTitle(t('pen.edit_title') if pen else t('pen.add'))
        self.setMinimumSize(scale_px(720), scale_px(600))
        self._setup_ui()
        if pen:
            self._load()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        tabs = QTabWidget()

        def _scroll_tab():
            outer = QWidget()
            outer_layout = QVBoxLayout(outer)
            outer_layout.setContentsMargins(0, 0, 0, 0)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QScrollArea.Shape.NoFrame)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            body = QWidget()
            body_layout = QVBoxLayout(body)
            body_layout.setContentsMargins(8, 8, 8, 8)
            body_layout.setSpacing(12)
            scroll.setWidget(body)
            outer_layout.addWidget(scroll)
            return (outer, body_layout)
        simple_tab, cl = _scroll_tab()
        nib_tab, nib_tab_layout = _scroll_tab()
        details_tab, details_layout = _scroll_tab()
        notes_tab, notes_layout = _scroll_tab()
        grp = QGroupBox(t('ui.pen_widget.grundinformationen_f21faf66'))
        fl = QFormLayout(grp)
        self.brand_edit = QLineEdit()
        self.brand_edit.setPlaceholderText(t('ui.pen_widget.z_b_pilot_lamy_pelikan_47938cc8'))
        self.model_edit = QLineEdit()
        self.model_edit.setPlaceholderText(t('ui.pen_widget.z_b_custom_74_safari_8a21b820'))
        self.color_edit = QLineEdit()
        self.color_edit.setPlaceholderText(t('ui.pen_widget.z_b_schwarz_blau_demo_e75aa69a'))
        self.fs_combo = QComboBox()
        for val, lbl in _fill_systems():
            self.fs_combo.addItem(lbl, val)
        fl.addRow(t('ui.pen_widget.marke_8f88b7b4'), self.brand_edit)
        fl.addRow(t('ui.pen_widget.modell_86c7210d'), self.model_edit)
        fl.addRow(t('ui.pen_widget.farbe_76ffe348'), self.color_edit)
        fl.addRow(t('ui.pen_widget.fullsystem_dae24858'), self.fs_combo)
        img_row = QHBoxLayout()
        self.image_path_edit = QLineEdit()
        self.image_path_edit.setPlaceholderText(t('ui.pen_widget.optional_bildpfad_aa00f1fa'))
        self.image_path_edit.setReadOnly(True)
        img_btn = QPushButton(t('ui.pen_widget.bild_wahlen_6548dc08'))
        img_btn.clicked.connect(self._choose_image)
        image_lookup_btn = QPushButton(t('pen_dimensions.image_lookup_btn'))
        image_lookup_btn.setToolTip(t('pen_dimensions.image_lookup_tooltip'))
        image_lookup_btn.clicked.connect(self._open_pen_image_search)
        img_row.addWidget(self.image_path_edit, 1)
        img_row.addWidget(img_btn)
        img_row.addWidget(image_lookup_btn)
        fl.addRow(t('ui.pen_widget.bild_2ddce904'), img_row)
        cl.addWidget(grp)
        grp_nib = QGroupBox(t('ui.pen_widget.feder_assistent_8792407e'))
        fln = QFormLayout(grp_nib)
        nib_row = QHBoxLayout()
        self.nib_combo = QComboBox()
        self.nib_combo.addItem(t('ui.pen_widget.keine_feder_zuweisen_3fd8283e'), None)
        self._reload_nibs()
        new_nib_btn = QPushButton(t('ui.pen_widget.feder_erstellen_60f6eb6f'))
        new_nib_btn.setStyleSheet('background:#8e44ad;color:white;border:none;padding:5px 10px;border-radius:4px;')
        new_nib_btn.clicked.connect(self._create_nib_inline)
        nib_row.addWidget(self.nib_combo, 1)
        nib_row.addWidget(new_nib_btn)
        fln.addRow(t('ui.pen_widget.vorhandene_feder_3d3ecfa6'), nib_row)
        self.create_nib_cb = QCheckBox(t('ui.pen_widget.beim_speichern_automatisch_neue_feder_anlegen_un_3d0e654e'))
        self.create_nib_cb.setChecked(True)
        self.nib_brand_edit = QLineEdit()
        self.nib_brand_edit.setPlaceholderText(t('ui.pen_widget.z_b_schmidt_bock_jowo_pilot_aba0586d'))
        self.nib_fineness_edit = QLineEdit()
        self.nib_fineness_edit.setPlaceholderText(t('ui.pen_widget.z_b_ef_f_m_stub_semiflex_f_97d0d2cd'))
        self.nib_physical_edit = QLineEdit()
        self.nib_physical_edit.setPlaceholderText(t('ui.pen_widget.z_b_5_6_8_pilot_10_lamy_2000_ad13e3b2'))
        self.nib_material_edit = QLineEdit()
        self.nib_material_edit.setPlaceholderText(t('ui.pen_widget.z_b_stahl_14k_gold_18k_gold_titan_6a8b83a8'))
        self.nib_prop_cb = QCheckBox(t('ui.pen_widget.proprietare_feder_nicht_standard_kompatibel_0adff536'))
        self.nib_source_edit = QLineEdit()
        self.nib_source_edit.setPlaceholderText(t('ui.pen_widget.bezug_tuner_z_b_gravitas_fnf_nibsmith_5cb382ac'))
        self.nib_grind_edit = QLineEdit()
        self.nib_grind_edit.setPlaceholderText(t('ui.pen_widget.z_b_standard_italic_ef_light_italic_1eeb0040'))
        self.nib_nibmeister_edit = QLineEdit()
        self.nib_nibmeister_edit.setPlaceholderText(t('ui.pen_widget.z_b_landolt_nibsmith_eigenarbeit_39d81db9'))
        self.nib_feedback_spin = QSpinBox()
        self.nib_feedback_spin.setRange(1, 5)
        self.nib_feedback_spin.setValue(3)
        self.nib_feedback_spin.setSuffix(t('ui.pen_widget.1_glatt_5_feedback_kratzig_e3432cba'))
        self.nib_stiff_spin = QSpinBox()
        self.nib_stiff_spin.setRange(1, 5)
        self.nib_stiff_spin.setValue(4)
        self.nib_stiff_spin.setSuffix(t('ui.pen_widget.1_sehr_weich_flex_5_sehr_steif_fcf96d7c'))
        self.nib_label_edit = QLineEdit()
        self.nib_label_edit.setPlaceholderText(t('ui.pen_widget.spitzname_optional_um_exemplare_zu_unterscheiden_96e32f08'))
        self.nib_combo.currentIndexChanged.connect(self._on_nib_combo_changed)
        fln.addRow('', self.create_nib_cb)
        fln.addRow(t('ui.pen_widget.feder_marke_4b2f5316'), self.nib_brand_edit)
        fln.addRow(t('ui.pen_widget.feinheit_e3285e74'), self.nib_fineness_edit)
        fln.addRow(t('ui.pen_widget.baugroe_330bb87f'), self.nib_physical_edit)
        fln.addRow(t('ui.pen_widget.federmaterial_4a9fc501'), self.nib_material_edit)
        fln.addRow('', self.nib_prop_cb)
        fln.addRow(t('ui.pen_widget.bezug_tuner_436b44fb'), self.nib_source_edit)
        fln.addRow(t('ui.pen_widget.schliff_grind_4dd6197e'), self.nib_grind_edit)
        fln.addRow(t('ui.pen_widget.nibmeister_995b4e58'), self.nib_nibmeister_edit)
        fln.addRow(t('ui.pen_widget.steifigkeit_feder_b2f9f29d'), self.nib_stiff_spin)
        fln.addRow(t('ui.pen_widget.feder_feedback_52e130c7'), self.nib_feedback_spin)
        fln.addRow(t('ui.pen_widget.spitzname_9dfd3cea'), self.nib_label_edit)
        nib_tab_layout.addWidget(grp_nib)
        grp_setup = QGroupBox(t('ui.pen_widget.einbau_setup_diese_feder_in_diesem_fuller_8ff0f3ea'))
        fls = QFormLayout(grp_setup)
        self.setup_label_edit = QLineEdit()
        self.setup_label_edit.setPlaceholderText(t('ui.pen_widget.z_b_gravitas_ef_im_jinhao_x750_3cbcdf3a'))
        self.setup_feed_type_edit = QLineEdit()
        self.setup_feed_type_edit.setPlaceholderText(t('ui.pen_widget.z_b_jinhao_feed_gravitas_feed_ebonit_feed_7fc1b142'))
        self.setup_feed_notes_edit = QTextEdit()
        self.setup_feed_notes_edit.setMaximumHeight(scale_px(70))
        self.setup_feed_notes_edit.setPlaceholderText(t('ui.pen_widget.feed_einbau_notiz_flow_verandert_sitzt_eng_steif_72799cc9'))
        self.setup_flow_spin = QSpinBox()
        self.setup_flow_spin.setRange(1, 5)
        self.setup_flow_spin.setValue(3)
        self.setup_flow_spin.setSuffix(t('ui.pen_widget.1_trocken_5_sehr_nass_0ad77eb3'))
        self.setup_stiff_spin = QSpinBox()
        self.setup_stiff_spin.setRange(1, 5)
        self.setup_stiff_spin.setValue(3)
        self.setup_stiff_spin.setSuffix(t('ui.pen_widget.1_weicher_eindruck_5_steifer_eindruck_61166a0a'))
        self.setup_feedback_spin = QSpinBox()
        self.setup_feedback_spin.setRange(1, 5)
        self.setup_feedback_spin.setValue(3)
        self.setup_feedback_spin.setSuffix(t('ui.pen_widget.1_glatt_5_feedback_kratzig_e3432cba'))
        self.setup_compat_notes_edit = QTextEdit()
        self.setup_compat_notes_edit.setMaximumHeight(scale_px(70))
        self.setup_compat_notes_edit.setPlaceholderText(t('ui.pen_widget.passt_mechanisch_aber_andere_haptik_flow_wegen_f_a1be9931'))
        self.setup_feel_notes_edit = QTextEdit()
        self.setup_feel_notes_edit.setMaximumHeight(scale_px(80))
        self.setup_feel_notes_edit.setPlaceholderText(t('ui.pen_widget.schreibgefuhl_dieser_kombination_09575282'))
        fls.addRow(t('ui.pen_widget.setup_name_f87fc0cd'), self.setup_label_edit)
        fls.addRow(t('ui.pen_widget.feed_im_fuller_1feb69c7'), self.setup_feed_type_edit)
        fls.addRow(t('ui.pen_widget.feed_notiz_cccd9366'), self.setup_feed_notes_edit)
        fls.addRow(t('ui.pen_widget.setup_flow_549866ff'), self.setup_flow_spin)
        fls.addRow(t('ui.pen_widget.setup_steifigkeit_8093b872'), self.setup_stiff_spin)
        fls.addRow(t('ui.pen_widget.setup_feedback_a819ed1f'), self.setup_feedback_spin)
        fls.addRow(t('ui.pen_widget.kompatibilitatsnotiz_2a338601'), self.setup_compat_notes_edit)
        fls.addRow(t('ui.pen_widget.setup_gefuhl_9f29934c'), self.setup_feel_notes_edit)
        nib_tab_layout.addWidget(grp_setup)
        grp_compat = QGroupBox(t('ui.pen_widget.feder_kompatibilitat_048161b5'))
        flc = QFormLayout(grp_compat)
        self.compat_edit = QTextEdit()
        self.compat_edit.setMaximumHeight(scale_px(80))
        self.compat_edit.setPlaceholderText(t('ui.pen_widget.z_b_schmidt_6_bock_250_jowo_6_4322d51a'))
        self.incompat_edit = QTextEdit()
        self.incompat_edit.setMaximumHeight(scale_px(80))
        self.incompat_edit.setPlaceholderText(t('ui.pen_widget.z_b_pilot_proprietar_lamy_2000_sailor_21k_d5c3772f'))
        flc.addRow(t('ui.pen_widget.kompatibel_4ec0f2cf'), self.compat_edit)
        flc.addRow(t('ui.pen_widget.nicht_kompatibel_357daa34'), self.incompat_edit)
        nib_tab_layout.addWidget(grp_compat)
        nib_tab_layout.addStretch(1)
        grp2 = QGroupBox(t('ui.pen_widget.kauf_wert_455a3e9c'))
        fl2 = QFormLayout(grp2)
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat(LocaleService.instance().qt_date_format)
        default_cur = LocaleService.instance().currency
        currencies = ['CHF', 'EUR', 'USD', 'GBP']
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0, 99999)
        self.price_spin.setDecimals(2)
        self.market_spin = QDoubleSpinBox()
        self.market_spin.setRange(0, 99999)
        self.market_spin.setDecimals(2)
        self.insur_spin = QDoubleSpinBox()
        self.insur_spin.setRange(0, 99999)
        self.insur_spin.setDecimals(2)
        self.price_currency_combo = QComboBox()
        populate_currency_combo(self.price_currency_combo, default_cur, currencies)
        self.market_currency_combo = QComboBox()
        populate_currency_combo(self.market_currency_combo, default_cur, currencies)
        self.insurance_currency_combo = QComboBox()
        populate_currency_combo(self.insurance_currency_combo, default_cur, currencies)
        bind_currency_combo(self.price_currency_combo, self.price_spin)
        bind_currency_combo(self.market_currency_combo, self.market_spin)
        bind_currency_combo(self.insurance_currency_combo, self.insur_spin)
        fl2.addRow(t('ui.pen_widget.kaufdatum_76cc01cf'), self.date_edit)
        fl2.addRow(t('ui.pen_widget.kaufpreis_6ae12ade'), self.price_spin)
        fl2.addRow(t('ui.pen_widget.kaufpreis_wahrung_2400553f'), self.price_currency_combo)
        fl2.addRow(t('ui.pen_widget.marktwert_6e0161c8'), self.market_spin)
        fl2.addRow(t('ui.pen_widget.marktwert_wahrung_08791540'), self.market_currency_combo)
        fl2.addRow(t('ui.pen_widget.versicherungswert_8d05db42'), self.insur_spin)
        fl2.addRow(t('ui.pen_widget.versicherungswert_wahrung_34a1f918'), self.insurance_currency_combo)
        details_layout.addWidget(grp2)
        grp3 = QGroupBox(t('ui.pen_widget.abmessungen_73a105d5'))
        fl3 = QFormLayout(grp3)
        self.len_spin = QDoubleSpinBox()
        self.len_spin.setRange(0, 500)
        self.len_spin.setSuffix(' mm')
        self.uncapped_spin = QDoubleSpinBox()
        self.uncapped_spin.setRange(0, 500)
        self.uncapped_spin.setSuffix(' mm')
        self.posted_spin = QDoubleSpinBox()
        self.posted_spin.setRange(0, 500)
        self.posted_spin.setSuffix(' mm')
        self.dia_spin = QDoubleSpinBox()
        self.dia_spin.setRange(0, 100)
        self.dia_spin.setSuffix(' mm')
        self.section_dia_spin = QDoubleSpinBox()
        self.section_dia_spin.setRange(0, 100)
        self.section_dia_spin.setSuffix(' mm')
        self.wt_spin = QDoubleSpinBox()
        self.wt_spin.setRange(0, 500)
        self.wt_spin.setSuffix(' g')
        fl3.addRow(t('ui.pen_widget.lange_geschlossen_fda56e6e'), self.len_spin)
        fl3.addRow(t('ui.pen_widget.lange_offen_ecbdec65'), self.uncapped_spin)
        fl3.addRow(t('ui.pen_widget.lange_gepostet_fb30f578'), self.posted_spin)
        fl3.addRow(t('ui.pen_widget.durchmesser_max_0c23304e'), self.dia_spin)
        fl3.addRow(t('ui.pen_widget.griffdurchmesser_e3ae853a'), self.section_dia_spin)
        fl3.addRow(t('ui.pen_widget.gewicht_b9a5a02b'), self.wt_spin)
        dim_lookup_btn = QPushButton(t('pen_dimensions.lookup_btn'))
        dim_lookup_btn.setToolTip(t('pen_dimensions.lookup_tooltip'))
        dim_lookup_btn.clicked.connect(self._lookup_dimensions)
        fl3.addRow('', dim_lookup_btn)
        details_layout.addWidget(grp3)
        grp_rot = QGroupBox(t('ui.pen_widget.rotation_tintenverbrauch_aa6d7e49'))
        flr = QFormLayout(grp_rot)
        self.capacity_spin = QDoubleSpinBox()
        self.capacity_spin.setRange(0, 10)
        self.capacity_spin.setDecimals(2)
        self.capacity_spin.setSingleStep(0.1)
        self.capacity_spin.setSuffix(' ml')
        self.pop_spin = QSpinBox()
        self.pop_spin.setRange(1, 5)
        self.pop_spin.setValue(3)
        self.pop_spin.setSuffix(' / 5')
        self.role_combo = QComboBox()
        for val, label in _rotation_roles():
            self.role_combo.addItem(label, val)
        self.role_combo.setToolTip(t('rotation.role_tooltip'))
        _role_edit_btn = QPushButton(t('rotation.role_edit_btn'))
        _role_edit_btn.setFixedWidth(80)
        _role_edit_btn.clicked.connect(lambda: RolePrefsDialog(self).exec())
        _role_row = QHBoxLayout()
        _role_row.addWidget(self.role_combo, 1)
        _role_row.addWidget(_role_edit_btn)
        self.theme_combo = QComboBox()
        for val, label in _rotation_themes():
            self.theme_combo.addItem(label, val)
        self.theme_combo.setToolTip(t('rotation.theme_tooltip'))
        self.must_rotation_cb = QCheckBox(t('ui.pen_widget.fuller_muss_in_jeder_rotation_dabei_sein_306c92ba'))
        flr.addRow(t('ui.pen_widget.fullvolumen_80c36e67'), self.capacity_spin)
        flr.addRow(t('ui.pen_widget.beliebtheit_6d7e4d54'), self.pop_spin)
        flr.addRow(t('rotation.role_label'), _role_row)
        flr.addRow(t('rotation.theme_label'), self.theme_combo)
        flr.addRow('', self.must_rotation_cb)
        details_layout.addWidget(grp_rot)
        grp4 = QGroupBox(t('ui.pen_widget.tags_f9c91062'))
        hl4 = QHBoxLayout(grp4)
        self.tag_cbs = {}
        for tag in TAG_KEYS:
            label = _tag_label(tag)
            cb = QCheckBox(label)
            hl4.addWidget(cb)
            self.tag_cbs[tag] = cb
        details_layout.addWidget(grp4)
        details_layout.addStretch(1)
        grp5 = QGroupBox(t('ui.pen_widget.notizen_7c75876c'))
        fl5 = QFormLayout(grp5)
        self.feel_edit = QTextEdit()
        self.feel_edit.setMaximumHeight(scale_px(90))
        self.feel_edit.setPlaceholderText(t('ui.pen_widget.schreibgefuhl_2fc5c2b4'))
        self.problem_edit = QTextEdit()
        self.problem_edit.setMaximumHeight(scale_px(90))
        self.problem_edit.setPlaceholderText(t('ui.pen_widget.kratzen_tintenprobleme_72193392'))
        self.clean_edit = QTextEdit()
        self.clean_edit.setMaximumHeight(scale_px(90))
        self.clean_edit.setPlaceholderText(t('ui.pen_widget.reinigungshinweise_3c2ab919'))
        fl5.addRow(t('ui.pen_widget.schreibgefuhl_bffe34f7'), self.feel_edit)
        fl5.addRow(t('ui.pen_widget.probleme_caf0e60d'), self.problem_edit)
        fl5.addRow(t('ui.pen_widget.reinigung_3f207efe'), self.clean_edit)
        notes_layout.addWidget(grp5)
        notes_layout.addStretch(1)
        tabs.addTab(simple_tab, t('ui.pen_widget.grunddaten_0e5009d7'))
        tabs.addTab(nib_tab, t('ui.pen_widget.feder_16045228'))
        tabs.addTab(details_tab, t('ui.pen_widget.details_wert_dda22f26'))
        tabs.addTab(notes_tab, t('ui.pen_widget.notizen_1c3583ea'))
        root.addWidget(tabs)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton(t('ui.pen_widget.abbrechen_bbc8a352'))
        cancel.setStyleSheet(BTN_MUTED)
        cancel.clicked.connect(self.reject)
        save = QPushButton(t('ui.pen_widget.speichern_26cb5264'))
        save.setStyleSheet(BTN_SUCCESS)
        save.clicked.connect(self._save)
        btn_row.addWidget(cancel)
        btn_row.addWidget(save)
        root.addLayout(btn_row)

    def _choose_image(self):
        path, _ = QFileDialog.getOpenFileName(self, t('ui.pen_widget.fullerbild_auswahlen_5a1ff15e'), str(Path.home()), t('ui.pen_widget.bilder_png_jpg_jpeg_webp_bmp_0a511660'))
        if path:
            self.image_path_edit.setText(path)

    def _open_pen_image_search(self):
        from logic.pen_dimensions_service import build_image_search_urls
        import webbrowser

        brand = self.brand_edit.text().strip()
        model = self.model_edit.text().strip()
        if not brand and not model:
            QMessageBox.information(self, t('pen_dimensions.lookup_title'), t('pen_dimensions.need_brand_model'))
            return
        # v0.2.84: manuelle Recherche breit/KI-freundlich statt enger
        # site:-Einschränkung. Der automatische Parser bleibt separat vorsichtig.
        try:
            data_dir = _data_dir()
        except Exception:
            data_dir = None
        urls = build_image_search_urls(brand, model, data_dir=data_dir)
        opened = False
        for url in urls[:2]:
            try:
                opened = bool(webbrowser.open(url)) or opened
            except Exception:
                pass
        QMessageBox.information(
            self,
            t('pen_dimensions.image_lookup_title'),
            t('pen_dimensions.image_lookup_message', url=urls[0] if urls else '', opened=t('common.yes') if opened else t('common.no')),
        )

    def _safe_image_basename(self) -> str:
        brand = self.brand_edit.text().strip() or 'pen'
        model = self.model_edit.text().strip() or 'model'
        safe_brand = ''.join((ch if ch.isalnum() else '_' for ch in brand))[:40]
        safe_model = ''.join((ch if ch.isalnum() else '_' for ch in model))[:60]
        return f'pen_{safe_brand}_{safe_model}_{int(datetime.now().timestamp())}'

    def _download_image_to_data_dir(self, url: str) -> Optional[str]:
        import urllib.parse
        import urllib.request

        raw = (url or '').strip()
        if not (raw.startswith('https://') or raw.startswith('http://')):
            return None
        parsed = urllib.parse.urlparse(raw)
        suffix = Path(parsed.path).suffix.lower()
        if suffix not in {'.png', '.jpg', '.jpeg', '.webp', '.bmp'}:
            suffix = '.jpg'
        img_dir = _data_dir() / 'images' / 'pens'
        img_dir.mkdir(parents=True, exist_ok=True)
        target = img_dir / f'{self._safe_image_basename()}{suffix}'
        try:
            req = urllib.request.Request(raw, headers={'User-Agent': 'FountainPenManager/collector-image-import'})
            with urllib.request.urlopen(req, timeout=12) as response:
                data = response.read(8 * 1024 * 1024 + 1)
            if not data or len(data) > 8 * 1024 * 1024:
                return None
            target.write_bytes(data)
            return str(target)
        except Exception:
            return None

    def _prepare_image_path(self) -> Optional[str]:
        # Rohpfad/URL zurückgeben. Der eigentliche Import erfolgt nach
        # session.flush(), weil dann die Füller-ID bekannt ist und die Datei
        # sauber unter data/media/pens/<id>_<marke>_<modell>/ landet.
        return self.image_path_edit.text().strip() or None

    def _reload_nibs(self, select_id=None):
        current = select_id if select_id is not None else self.nib_combo.currentData() if hasattr(self, 'nib_combo') else None
        if not hasattr(self, 'nib_combo'):
            return
        self.nib_combo.blockSignals(True)
        self.nib_combo.clear()
        self.nib_combo.addItem(t('ui.pen_widget.keine_feder_zuweisen_3fd8283e'), None)
        session = get_session()
        try:
            for n in session.query(Nib).order_by(Nib.manufacturer, Nib.size, Nib.grind).all():
                label = n.display_label
                if n.nibmeister and n.nibmeister not in label:
                    label += f' · {n.nibmeister}'
                self.nib_combo.addItem(label, n.id)
        finally:
            session.close()
        if current is not None:
            idx = self.nib_combo.findData(current)
            if idx >= 0:
                self.nib_combo.setCurrentIndex(idx)
        self.nib_combo.blockSignals(False)

    def _create_nib_inline(self):
        dlg = NibDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            session = get_session()
            try:
                data = dlg.get_data()
                data['format_id'] = dlg.resolve_format(session)
                nib = Nib(**data)
                session.add(nib)
                session.commit()
                AppEventBus.instance().nibs_changed.emit()
                new_id = nib.id
            except Exception as e:
                QMessageBox.critical(self, t('ui.pen_widget.fehler_46938af3'), str(e))
                return
            finally:
                session.close()
            self._reload_nibs(new_id)

    def _lookup_dimensions(self):
        """Cache/Online-Hilfe für Füller-Referenzdaten.

        Werte werden nur aus der lokalen Cachedatei übernommen. Ohne Treffer
        öffnet die App Websuchen für technische Daten und Bilder; der Nutzer
        entscheidet danach bewusst, was in den Cache oder direkt ins Formular kommt.
        """
        from logic.pen_dimensions_service import default_dimension_cache_path, lookup_pen_dimensions, merge_dimension_cache
        import webbrowser

        brand = self.brand_edit.text().strip()
        model = self.model_edit.text().strip()
        if not brand and not model:
            QMessageBox.information(self, t('pen_dimensions.lookup_title'), t('pen_dimensions.need_brand_model'))
            return

        cache_path = default_dimension_cache_path(_data_dir())
        result = lookup_pen_dimensions(brand, model, cache_path=cache_path, allow_online=True)
        suggestion = result.best
        if suggestion and suggestion.has_reference_data():
            lines = []
            labels = {
                'length_mm': t('ui.pen_widget.lange_geschlossen_fda56e6e'),
                'length_uncapped_mm': t('ui.pen_widget.lange_offen_ecbdec65'),
                'length_posted_mm': t('ui.pen_widget.lange_gepostet_fb30f578'),
                'diameter_mm': t('ui.pen_widget.durchmesser_max_0c23304e'),
                'section_diameter_mm': t('ui.pen_widget.griffdurchmesser_e3ae853a'),
                'weight_g': t('ui.pen_widget.gewicht_b9a5a02b'),
                'ink_capacity_ml': t('ui.pen_widget.fullvolumen_80c36e67'),
                'fill_system': t('ui.pen_widget.fullsystem_dae24858'),
                'image_url': t('ui.pen_widget.bild_2ddce904'),
            }
            for field, value in suggestion.values().items():
                unit = 'g' if field == 'weight_g' else 'mm'
                lines.append(f"{labels.get(field, field)}: {value:g} {unit}")
            if suggestion.ink_capacity_ml:
                lines.append(f"{labels['ink_capacity_ml']}: {suggestion.ink_capacity_ml:g} ml")
            if suggestion.fill_system:
                lines.append(f"{labels['fill_system']}: {_fill_system_label(suggestion.fill_system)}")
            if suggestion.all_image_urls():
                lines.append(f"{labels['image_url']}: {suggestion.all_image_urls()[0]}")
            question = t(
                'pen_dimensions.apply_question',
                brand=suggestion.brand,
                model=suggestion.model,
                source=suggestion.source or 'cache',
                values='\n'.join(lines),
            )
            if QMessageBox.question(self, t('pen_dimensions.apply_title'), question) == QMessageBox.StandardButton.Yes:
                mapping = {
                    'length_mm': self.len_spin,
                    'length_uncapped_mm': self.uncapped_spin,
                    'length_posted_mm': self.posted_spin,
                    'diameter_mm': self.dia_spin,
                    'section_diameter_mm': self.section_dia_spin,
                    'weight_g': self.wt_spin,
                }
                for field, value in suggestion.values().items():
                    spin = mapping.get(field)
                    if spin is not None and spin.value() <= 0:
                        spin.setValue(value)
                if suggestion.ink_capacity_ml and self.capacity_spin.value() <= 0:
                    self.capacity_spin.setValue(float(suggestion.ink_capacity_ml))
                if suggestion.fill_system:
                    # Fill system has a technical default (converter).  It is safe to
                    # improve an untouched default, but never override a deliberate choice.
                    current = self.fs_combo.currentData()
                    idx = self.fs_combo.findData(suggestion.fill_system)
                    if idx >= 0 and (current in (None, 'converter') or not current):
                        self.fs_combo.setCurrentIndex(idx)
                if suggestion.all_image_urls() and not self.image_path_edit.text().strip():
                    self.image_path_edit.setText(suggestion.all_image_urls()[0])
                # Online suggestions become deterministic after the user accepted
                # them once. This keeps later edits offline and avoids repeated
                # network lookups for the same pen.
                if result.message_code == 'online_match':
                    try:
                        merge_dimension_cache(cache_path, suggestion)
                    except Exception:
                        pass
            return

        def _open_first_stages(urls) -> bool:
            any_opened = False
            for url in list(urls or ())[:2]:
                try:
                    any_opened = bool(webbrowser.open(url)) or any_opened
                except Exception:
                    pass
            return any_opened

        opened = _open_first_stages(result.search_urls)
        opened_image = _open_first_stages(result.image_search_urls)
        url_text = result.search_urls[0] if result.search_urls else ''
        image_url_text = result.image_search_urls[0] if result.image_search_urls else ''
        QMessageBox.information(
            self,
            t('pen_dimensions.no_cache_title'),
            t(
                'pen_dimensions.no_cache_message',
                path=str(cache_path),
                url=url_text,
                image_url=image_url_text,
                opened=t('common.yes') if opened else t('common.no'),
                image_opened=t('common.yes') if opened_image else t('common.no'),
            ),
        )

    def _load(self):
        p = self.pen
        self.brand_edit.setText(p.brand or '')
        self.model_edit.setText(p.model or '')
        self.color_edit.setText(p.color or '')
        self.image_path_edit.setText(getattr(p, 'image_path', None) or '')
        for i, (val, _) in enumerate(_fill_systems()):
            if val == p.fill_system:
                self.fs_combo.setCurrentIndex(i)
                break
        if p.purchase_date:
            d = p.purchase_date
            self.date_edit.setDate(QDate(d.year, d.month, d.day))
        self.price_spin.setValue(p.purchase_price or 0)
        self.market_spin.setValue(p.current_market_value or 0)
        self.insur_spin.setValue(p.insurance_value or 0)
        set_combo_currency(self.price_currency_combo, getattr(p, 'purchase_currency', None))
        set_combo_currency(
            self.market_currency_combo,
            getattr(p, 'market_currency', None) or getattr(p, 'purchase_currency', None),
        )
        set_combo_currency(self.insurance_currency_combo, getattr(p, 'insurance_currency', None))
        self.len_spin.setValue(p.length_mm or 0)
        self.uncapped_spin.setValue(getattr(p, 'length_uncapped_mm', None) or 0)
        self.posted_spin.setValue(getattr(p, 'length_posted_mm', None) or 0)
        self.dia_spin.setValue(p.diameter_mm or 0)
        self.section_dia_spin.setValue(getattr(p, 'section_diameter_mm', None) or 0)
        self.wt_spin.setValue(p.weight_g or 0)
        self.capacity_spin.setValue(getattr(p, 'ink_capacity_ml', None) or 0)
        self.pop_spin.setValue(getattr(p, 'popularity_rating', 3) or 3)
        self.must_rotation_cb.setChecked(bool(getattr(p, 'must_include_in_rotation', False)))
        role_idx = self.role_combo.findData(getattr(p, 'rotation_role', None) or 'writer')
        if role_idx >= 0:
            self.role_combo.setCurrentIndex(role_idx)
        theme_idx = self.theme_combo.findData(getattr(p, 'rotation_theme', None))
        if theme_idx >= 0:
            self.theme_combo.setCurrentIndex(theme_idx)
        for tag in p.tags_list:
            if tag in self.tag_cbs:
                self.tag_cbs[tag].setChecked(True)
        self.feel_edit.setPlainText(p.writing_feel_notes or '')
        self.problem_edit.setPlainText(p.problem_notes or '')
        self.clean_edit.setPlainText(p.cleaning_notes or '')
        if getattr(p, 'compatible_nibs', None):
            self.compat_edit.setPlainText(p.compatible_nibs or '')
        if getattr(p, 'incompatible_nibs', None):
            self.incompat_edit.setPlainText(p.incompatible_nibs or '')
        if p.nib_id:
            idx = self.nib_combo.findData(p.nib_id)
            if idx >= 0:
                self.nib_combo.setCurrentIndex(idx)
                self.create_nib_cb.setChecked(False)
        if p.nib:
            self.nib_brand_edit.setText(p.nib.effective_manufacturer or '')
            self.nib_fineness_edit.setText(p.nib.size or '')
            self.nib_physical_edit.setText(p.nib.effective_physical_size or '')
            self.nib_material_edit.setText(getattr(p.nib, 'material', None) or '')
            self.nib_prop_cb.setChecked(bool(p.nib.effective_is_proprietary))
            self.nib_source_edit.setText(getattr(p.nib, 'source', None) or '')
            self.nib_grind_edit.setText(getattr(p.nib, 'grind', None) or '')
            self.nib_nibmeister_edit.setText(getattr(p.nib, 'nibmeister', None) or '')
            self.nib_stiff_spin.setValue(int(getattr(p.nib, 'stiffness_level', 4) or 4))
            self.nib_feedback_spin.setValue(int(getattr(p.nib, 'feedback_level', 3) or 3))
            self.nib_label_edit.setText(getattr(p.nib, 'label', None) or '')
        setup = getattr(p, 'active_nib_setup', None)
        if setup:
            self.setup_label_edit.setText(getattr(setup, 'setup_label', None) or '')
            self.setup_feed_type_edit.setText(getattr(setup, 'feed_type', None) or '')
            self.setup_feed_notes_edit.setPlainText(getattr(setup, 'feed_notes', None) or '')
            self.setup_flow_spin.setValue(int(getattr(setup, 'flow_level', 3) or 3))
            self.setup_stiff_spin.setValue(int(getattr(setup, 'stiffness_feel_level', 3) or 3))
            self.setup_feedback_spin.setValue(int(getattr(setup, 'feedback_level', 3) or 3))
            self.setup_compat_notes_edit.setPlainText(getattr(setup, 'compatibility_notes', None) or '')
            self.setup_feel_notes_edit.setPlainText(getattr(setup, 'feel_notes', None) or '')

    def _on_nib_combo_changed(self, _index: int):
        """Nib-Combo: Felder automatisch aus bestehender Feder befüllen oder für neue Eingabe freigeben."""
        from database.models import Nib as _Nib
        nib_id = self.nib_combo.currentData()
        self.create_nib_cb.setChecked(nib_id is None)
        inline_widgets = [self.nib_brand_edit, self.nib_fineness_edit, self.nib_physical_edit, self.nib_material_edit, self.nib_prop_cb, self.nib_source_edit, self.nib_grind_edit, self.nib_nibmeister_edit, self.nib_stiff_spin, self.nib_feedback_spin, self.nib_label_edit]
        if nib_id is not None:
            session = get_session()
            try:
                nib = session.get(_Nib, nib_id)
                if nib:
                    self.nib_brand_edit.setText(nib.effective_manufacturer or '')
                    self.nib_fineness_edit.setText(nib.size or '')
                    self.nib_physical_edit.setText(nib.effective_physical_size or '')
                    self.nib_material_edit.setText(getattr(nib, 'material', None) or '')
                    self.nib_prop_cb.setChecked(bool(nib.effective_is_proprietary))
                    self.nib_source_edit.setText(getattr(nib, 'source', None) or '')
                    self.nib_grind_edit.setText(getattr(nib, 'grind', None) or '')
                    self.nib_nibmeister_edit.setText(getattr(nib, 'nibmeister', None) or '')
                    self.nib_stiff_spin.setValue(int(getattr(nib, 'stiffness_level', 4) or 4))
                    self.nib_feedback_spin.setValue(int(getattr(nib, 'feedback_level', 3) or 3))
                    self.nib_label_edit.setText(getattr(nib, 'label', None) or '')
            finally:
                session.close()
            for w in inline_widgets:
                w.setEnabled(False)
            self.create_nib_cb.setVisible(False)
        else:
            self.nib_brand_edit.setText('')
            self.nib_fineness_edit.setText('')
            self.nib_physical_edit.setText('')
            self.nib_material_edit.setText('')
            self.nib_prop_cb.setChecked(False)
            self.nib_source_edit.setText('')
            self.nib_grind_edit.setText('')
            self.nib_nibmeister_edit.setText('')
            self.nib_stiff_spin.setValue(4)
            self.nib_feedback_spin.setValue(3)
            self.nib_label_edit.setText('')
            for w in inline_widgets:
                w.setEnabled(True)
            self.create_nib_cb.setVisible(True)

    def _save(self):
        if not self.brand_edit.text().strip():
            QMessageBox.warning(self, t('ui.pen_widget.pflichtfeld_485a6d5a'), t('ui.pen_widget.bitte_marke_eingeben_bf9c8a50'))
            return
        if not self.model_edit.text().strip():
            QMessageBox.warning(self, t('ui.pen_widget.pflichtfeld_485a6d5a'), t('ui.pen_widget.bitte_modell_eingeben_f7b71446'))
            return
        self.accept()

    def get_data(self) -> dict:
        d = self.date_edit.date()
        tags = [t for t, cb in self.tag_cbs.items() if cb.isChecked()]
        return {'brand': self.brand_edit.text().strip(), 'model': self.model_edit.text().strip(), 'color': self.color_edit.text().strip() or None, 'fill_system': self.fs_combo.currentData(), 'nib_id': self.nib_combo.currentData(), 'compatible_nibs': self.compat_edit.toPlainText().strip() or None, 'incompatible_nibs': self.incompat_edit.toPlainText().strip() or None, 'purchase_date': datetime(d.year(), d.month(), d.day()), 'purchase_price': self.price_spin.value() or None, 'purchase_currency': current_currency(self.price_currency_combo), 'current_market_value': self.market_spin.value() or None, 'market_currency': current_currency(self.market_currency_combo), 'insurance_value': self.insur_spin.value() or None, 'insurance_currency': current_currency(self.insurance_currency_combo), 'length_mm': self.len_spin.value() or None, 'length_uncapped_mm': self.uncapped_spin.value() or None, 'length_posted_mm': self.posted_spin.value() or None, 'diameter_mm': self.dia_spin.value() or None, 'section_diameter_mm': self.section_dia_spin.value() or None, 'weight_g': self.wt_spin.value() or None, 'image_path': self._prepare_image_path(), 'ink_capacity_ml': self.capacity_spin.value() or None, 'popularity_rating': self.pop_spin.value(), 'must_include_in_rotation': self.must_rotation_cb.isChecked(), 'rotation_role': self.role_combo.currentData() or 'writer', 'rotation_theme': self.theme_combo.currentData(), 'tags': ','.join(tags) or None, 'writing_feel_notes': self.feel_edit.toPlainText().strip() or None, 'problem_notes': self.problem_edit.toPlainText().strip() or None, 'cleaning_notes': self.clean_edit.toPlainText().strip() or None}

    def should_create_nib(self) -> bool:
        return bool(self.create_nib_cb.isChecked() and (not self.nib_combo.currentData()) and (self.nib_brand_edit.text().strip() or self.nib_fineness_edit.text().strip() or self.nib_physical_edit.text().strip() or self.nib_material_edit.text().strip() or self.nib_grind_edit.text().strip()))

    def get_inline_nib_data(self) -> dict:
        """Felder für die neue Feder.

        Unit-Felder werden als Nib-Spalten gespeichert. Die Format-Felder werden
        mit '_format_' präfixiert übergeben und im _resolve_nib zu einem
        NibFormat (dedupliziert) aufgelöst.
        """
        return {'size': self.nib_fineness_edit.text().strip() or None, 'material': self.nib_material_edit.text().strip() or None, 'source': self.nib_source_edit.text().strip() or None, 'grind': self.nib_grind_edit.text().strip() or None, 'nibmeister': self.nib_nibmeister_edit.text().strip() or None, 'stiffness_level': int(self.nib_stiff_spin.value()), 'label': self.nib_label_edit.text().strip() or None, 'feedback_level': int(self.nib_feedback_spin.value()), 'is_flexible': int(self.nib_stiff_spin.value()) <= 2, 'notes': 'Automatisch beim Füller angelegt', 'manufacturer': self.nib_brand_edit.text().strip() or None, 'physical_size': self.nib_physical_edit.text().strip() or None, 'is_proprietary': self.nib_prop_cb.isChecked(), '_format_manufacturer': self.nib_brand_edit.text().strip() or None, '_format_physical_size': self.nib_physical_edit.text().strip() or None, '_format_is_proprietary': self.nib_prop_cb.isChecked()}

    def get_nib_setup_data(self) -> dict:
        """Setup-Daten: Feder + Feed + konkreter Füller.

        Diese Werte werden NICHT an der Feder gespeichert, weil dieselbe Feder
        in einem anderen Füller anders schreiben kann.
        """
        return {'setup_label': self.setup_label_edit.text().strip() or None, 'feed_type': self.setup_feed_type_edit.text().strip() or None, 'feed_notes': self.setup_feed_notes_edit.toPlainText().strip() or None, 'flow_level': int(self.setup_flow_spin.value()), 'wetness_feel_level': int(self.setup_flow_spin.value()), 'stiffness_feel_level': int(self.setup_stiff_spin.value()), 'feedback_level': int(self.setup_feedback_spin.value()), 'compatibility_notes': self.setup_compat_notes_edit.toPlainText().strip() or None, 'feel_notes': self.setup_feel_notes_edit.toPlainText().strip() or None}

class LoadInkDialog(QDialog):
    """Dialog zum Einfüllen einer Tinte mit Regelprüfung."""

    def __init__(self, parent=None, pen_id: int=None):
        super().__init__(parent)
        self.pen_id = pen_id
        self.setWindowTitle(t('ui.pen_widget.tinte_einfullen_4b5d3bbe'))
        self.setMinimumWidth(520)
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        session = get_session()
        try:
            pen = session.get(Pen, self.pen_id)
            if pen:
                hdr = QLabel(t('ui.pen_widget.load_header_html', pen=f'{pen.brand} {pen.model}', fill_system=_fill_system_label(pen.fill_system)))
                hdr.setStyleSheet('font-size:14px; padding:8px;')
                root.addWidget(hdr)
                load = pen.current_ink_load
                if load:
                    ink = session.get(Ink, load.ink_id)
                    warn = QLabel(t('ui.pen_widget.already_inked_warning_html', ink=f'{ink.brand} {ink.name}'))
                    warn.setStyleSheet('color:#e74c3c; background:#fde8e8; padding:8px; border-radius:5px;')
                    root.addWidget(warn)
            fl = QFormLayout()
            self.ink_combo = QComboBox()
            self.ink_combo.addItem(t('ui.pen_widget.tinte_auswahlen_0ebd46d0'), None)
            inks = session.query(Ink).filter_by(is_empty=False, is_archived=False).order_by(Ink.brand, Ink.name).all()
            if not inks:
                no_ink_lbl = QLabel(t('ui.pen_widget.keine_tinten_vorhanden_oder_alle_leer_archiviert_5462a386'))
                no_ink_lbl.setStyleSheet('color:#c0392b; background:#fde8e8; padding:10px; border-radius:5px;')
                no_ink_lbl.setWordWrap(True)
                root.addWidget(no_ink_lbl)
                ok_btn = QPushButton(t('ui.pen_widget.schliessen_5ffdcd4f'))
                ok_btn.clicked.connect(self.reject)
                root.addWidget(ok_btn)
                return
            for ink in inks:
                badges = []
                if ink.has_shimmer:
                    badges.append('Shimmer')
                if ink.is_pigment:
                    badges.append('Pigment')
                if ink.is_waterproof:
                    badges.append('WF')
                suffix = f" [{', '.join(badges)}]" if badges else ''
                self.ink_combo.addItem(f'{ink.brand} {ink.name}{suffix}', ink.id)
            ink_row = QHBoxLayout()
            ink_row.addWidget(self.ink_combo, 1)
            new_ink_btn = QPushButton(t('ui.pen_widget.tinte_erstellen_1aaf7725'))
            new_ink_btn.setStyleSheet('background:#3498db;color:white;border:none;padding:5px 10px;border-radius:4px;')
            new_ink_btn.clicked.connect(self._create_ink_inline)
            ink_row.addWidget(new_ink_btn)
            fl.addRow(t('ui.pen_widget.tinte_856cea06'), ink_row)
            self.fixed_pair_cb = QCheckBox(t('ui.pen_widget.diese_tinte_mit_diesem_fuller_verheiraten_immer__a45e5484'))
            self.volume_spin = QDoubleSpinBox()
            self.volume_spin.setRange(0, 10)
            self.volume_spin.setDecimals(2)
            self.volume_spin.setSingleStep(0.1)
            self.volume_spin.setSuffix(' ml')
            if pen and getattr(pen, 'ink_capacity_ml', None):
                self.volume_spin.setValue(pen.ink_capacity_ml)
            self.notes_edit = QLineEdit()
            self.notes_edit.setPlaceholderText(t('ui.pen_widget.optionale_notizen_9b9f7ceb'))
            fl.addRow(t('ui.pen_widget.verheiratet_2cbd44bb'), self.fixed_pair_cb)
            fl.addRow(t('ui.pen_widget.fullmenge_e11d58a4'), self.volume_spin)
            fl.addRow(t('ui.pen_widget.notizen_c1f3108d'), self.notes_edit)
            root.addLayout(fl)
            self.warn_lbl = QLabel('')
            self.warn_lbl.setWordWrap(True)
            self.warn_lbl.setMinimumHeight(60)
            self.warn_lbl.setStyleSheet('padding:8px; border-radius:5px;')
            root.addWidget(self.warn_lbl)
            self.ink_combo.currentIndexChanged.connect(self._check_rules)
        finally:
            session.close()
        br = QHBoxLayout()
        br.addStretch()
        cancel = QPushButton(t('ui.pen_widget.abbrechen_bbc8a352'))
        cancel.setStyleSheet(BTN_MUTED)
        cancel.clicked.connect(self.reject)
        self.ok_btn = QPushButton(t('ui.pen_widget.einfullen_da7f3141'))
        self.ok_btn.setStyleSheet(BTN_SUCCESS)
        self.ok_btn.clicked.connect(self._do_load)
        br.addWidget(cancel)
        br.addWidget(self.ok_btn)
        root.addLayout(br)

    def _reload_inks(self, select_id=None):
        current = select_id if select_id is not None else self.ink_combo.currentData()
        self.ink_combo.blockSignals(True)
        self.ink_combo.clear()
        self.ink_combo.addItem(t('ui.pen_widget.tinte_auswahlen_0ebd46d0'), None)
        session = get_session()
        try:
            inks = session.query(Ink).filter_by(is_empty=False, is_archived=False).order_by(Ink.brand, Ink.name).all()
            for ink in inks:
                badges = []
                if ink.has_shimmer:
                    badges.append('Shimmer')
                if ink.is_pigment:
                    badges.append('Pigment')
                if ink.is_waterproof:
                    badges.append('WF')
                suffix = f" [{', '.join(badges)}]" if badges else ''
                self.ink_combo.addItem(f'{ink.brand} {ink.name}{suffix}', ink.id)
        finally:
            session.close()
        if current is not None:
            idx = self.ink_combo.findData(current)
            if idx >= 0:
                self.ink_combo.setCurrentIndex(idx)
        self.ink_combo.blockSignals(False)
        self._check_rules()

    def _create_ink_inline(self):
        dlg = InkDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            session = get_session()
            try:
                ink = Ink(**dlg.get_data())
                session.add(ink)
                session.commit()
                AppEventBus.instance().inks_changed.emit()
                new_id = ink.id
            except Exception as e:
                QMessageBox.critical(self, t('ui.pen_widget.fehler_46938af3'), str(e))
                return
            finally:
                session.close()
            self._reload_inks(new_id)

    def _check_rules(self):
        ink_id = self.ink_combo.currentData()
        if not ink_id:
            self.warn_lbl.setText('')
            return
        session = get_session()
        try:
            pen = session.get(Pen, self.pen_id)
            ink = session.get(Ink, ink_id)
            if pen and ink:
                engine = RuleEngine()
                violations = engine.check(pen, ink, session)
                if violations:
                    lines = []
                    worst = 'info'
                    for v in violations:
                        hard_suffix = ' (harte Regel)' if v.rule_type == 'hard' else ''
                        lines.append(f"{LEVEL_ICONS.get(v.warn_level, '⚠')}  {v.rule_name}: {v.description}{hard_suffix}")
                        effective_level = 'blocked' if v.rule_type == 'hard' else v.warn_level
                        if ['info', 'warning', 'critical', 'blocked'].index(effective_level) > ['info', 'warning', 'critical', 'blocked'].index(worst):
                            worst = effective_level
                    bg = {'info': '#e8f4fd', 'warning': '#fef9e7', 'critical': '#fde8d8', 'blocked': '#fde8e8'}
                    self.warn_lbl.setText('\n'.join(lines))
                    self.warn_lbl.setStyleSheet(f"background:{bg.get(worst, '#fff')}; padding:8px; border-radius:5px; color:#333;")
                else:
                    self.warn_lbl.setText(t('ui.pen_widget.keine_regelverletzungen_kombination_empfohlen_02cea1dd'))
                    self.warn_lbl.setStyleSheet('background:#e8f8e8; padding:8px; border-radius:5px; color:#27ae60;')
        finally:
            session.close()

    def _do_load(self):
        ink_id = self.ink_combo.currentData()
        if not ink_id:
            QMessageBox.warning(self, t('ui.pen_widget.auswahl_e80108ad'), t('ui.pen_widget.bitte_eine_tinte_auswahlen_8b472c36'))
            return
        notes = self.notes_edit.text().strip() or None
        volume = self.volume_spin.value() or None
        fixed_pairing = self.fixed_pair_cb.isChecked()
        override_reason = ''
        session = get_session()
        try:
            pen = session.get(Pen, self.pen_id)
            ink = session.get(Ink, ink_id)
            if pen and ink:
                engine = RuleEngine()
                violations = engine.check(pen, ink, session)
                needs_override = bool(violations and any((v.warn_level in ('blocked', 'critical', 'warning') or v.rule_type == 'hard' for v in violations)))
                if needs_override:
                    lines = '\n'.join((f"{LEVEL_ICONS.get(v.warn_level, '⚠')} {v.rule_name}: {v.description}" + (' (harte Regel)' if v.rule_type == 'hard' and v.warn_level != 'blocked' else '') for v in violations if v.warn_level in ('blocked', 'critical', 'warning') or v.rule_type == 'hard'))
                    reason, ok = QInputDialog.getText(self, t('ui.pen_widget.regeluberschreibung_bestatigen_e8bb1617'), t('ui.pen_widget.override_reason_prompt', rules=lines))
                    if not ok:
                        return
                    override_reason = reason.strip() or 'Manuelle Befüllung bewusst bestätigt'
        finally:
            session.close()
        ok, msg = RotationEngine().fill_pen(self.pen_id, ink_id, override_reason=override_reason, source='manual', notes=notes, volume_ml=volume, fixed_pairing=fixed_pairing, close_open_loads=True)
        if ok:
            self.accept()
        else:
            QMessageBox.warning(self, t('ui.pen_widget.einfullen_nicht_moglich_00581a84'), msg)
