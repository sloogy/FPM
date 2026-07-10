"""
Tintenverwaltung – CRUD mit Farbevorschau und Eigenschafts-Checkboxen.
"""
from datetime import datetime
import csv
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QDialog, QFormLayout, QComboBox, QDoubleSpinBox, QDateEdit,
    QTextEdit, QCheckBox, QGroupBox, QScrollArea, QMessageBox,
    QSplitter, QFrame, QSpinBox, QSlider, QMenu, QFileDialog,
    QStackedWidget,
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor, QFont, QPainter, QBrush
from ui.common import EmptyStateWidget, ImportPreviewDialog
from logic.event_bus import AppEventBus
from logic.enthusiast_lab_service import ink_stock_rows
from logic.ink_reach_service import ink_reach_row

from ui.ui_scale import scale_px
from database.db import get_session
from database.models import Ink
from i18n.translator import LocaleService, format_money, format_date, t
from logic.color_family_service import normalize_color_family
from ui.theme import BTN_ACCENT, BTN_MUTED, BTN_PRIMARY, BTN_SECONDARY, BTN_SUCCESS

COLOR_FAMILY_KEYS = [
    "blue", "black", "red", "green", "purple", "brown",
    "orange", "grey", "teal", "turquoise", "other",
]

def _color_families():
    return [(key, t(f"ink.color_families.{key}")) for key in COLOR_FAMILY_KEYS]

def _ink_usage_tags_translated():
    return [
        ("edc",           t("rotation.tag_edc")),
        ("agenda",        t("rotation.tag_agenda")),
        ("work",          t("rotation.tag_work")),
        ("business",      t("rotation.tag_business")),
        ("document",      t("rotation.tag_document")),
        ("archive",       t("rotation.tag_archive")),
        ("journal",       t("rotation.tag_journal")),
        ("letter",        t("rotation.tag_letter")),
        ("creative",      t("rotation.tag_creative")),
        ("sheen_showcase",t("rotation.tag_sheen")),
        ("shading",       t("rotation.tag_shading")),
        ("fine_nib",      t("rotation.tag_fine_nib")),
        ("broad_nib",     t("rotation.tag_broad_nib")),
        ("cheap_paper",   t("rotation.tag_cheap_paper")),
        ("easy_clean",    t("rotation.tag_easy_clean")),
        ("collector_safe",t("rotation.tag_collector")),
        ("vintage_safe",  t("rotation.tag_vintage")),
        ("testing",       t("rotation.tag_testing")),
        ("waterproof",    t("rotation.tag_waterproof")),
    ]
# backward-compat alias (Inline-Referenzen via dict(INK_USAGE_TAGS) bleiben gültig)
INK_USAGE_TAGS = _ink_usage_tags_translated()


def _split_csv(value):
    if not value:
        return []
    return [v.strip() for v in str(value).split(",") if v.strip()]


def _color_item(hex_color: str) -> QTableWidgetItem:
    """Tabellenzelle mit farbigem Punkt."""
    item = QTableWidgetItem(hex_color or "")
    if hex_color:
        item.setBackground(QColor(hex_color))
        item.setText("")
    return item


class InkWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._setup_ui()
        AppEventBus.instance().inks_changed.connect(self.refresh)
        self.refresh()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        # Header
        hdr = QHBoxLayout()
        title = QLabel(t('ui.ink_widget.tintenverwaltung_66dd8d2d'))
        title.setObjectName("page_title")
        hdr.addWidget(title)
        hdr.addStretch()

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(t('ui.ink_widget.suchen_77bc5fd4'))
        self.search_edit.setMinimumWidth(scale_px(220))
        self.search_edit.textChanged.connect(self._filter)
        hdr.addWidget(self.search_edit)

        add_btn = QPushButton(t('ui.ink_widget.tinte_hinzufugen_988b4827'))
        add_btn.setStyleSheet(BTN_PRIMARY)
        add_btn.clicked.connect(self._add)
        hdr.addWidget(add_btn)

        copy_btn = QPushButton(t('ui.ink_widget.tinte_kopieren_refill_5292695d'))
        copy_btn.setStyleSheet(BTN_ACCENT)
        copy_btn.clicked.connect(self._copy_refill)
        hdr.addWidget(copy_btn)

        import_btn = QPushButton(t('ui.ink_widget.tinten_importieren_ecbad5c5'))
        import_btn.setStyleSheet("background:#7f8c8d;color:white;border:none;padding:7px 14px;border-radius:5px;font-weight:bold;")
        import_btn.clicked.connect(self._import_inks)
        hdr.addWidget(import_btn)

        export_btn = QPushButton(t('ui.ink_widget.tinten_exportieren_a2cdc8a8'))
        export_btn.setStyleSheet(BTN_SECONDARY)
        export_btn.clicked.connect(self._export_inks)
        hdr.addWidget(export_btn)
        root.addLayout(hdr)

        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Linke Seite
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(8)

        self.stack = QStackedWidget()

        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels(
            [t('ui.ink_widget.farbe_65ff491c'), t('ui.ink_widget.marke_33a41668'), t('ui.ink_widget.name_ac10f3c6'), t('ui.ink_widget.farbfamilie_af08f17e'), t('ui.ink_widget.rest_8143b6eb'), t('ui.ink_widget.letzte_fullung_c92c3455'), t("ui.ink_widget.usage_header"), t('ui.ink_widget.sheen_acf03a5a'), t('ui.ink_widget.schimmer_5428d983'), t('ui.ink_widget.status_02e92391')]
        )
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 50)
        for i in (1, 2):
            hh.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
        for i in (3, 4, 5, 6, 7, 8, 9):
            hh.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.clicked.connect(self._on_select)
        self.table.doubleClicked.connect(self._edit)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)

        self._empty_state = EmptyStateWidget(
            icon="🫙",
            title=t("ui.ink_widget.empty_title"),
            subtitle=t("ui.ink_widget.empty_subtitle"),
            action_label=t("ui.ink_widget.empty_action"),
            action_slot=self._add,
        )
        self.stack.addWidget(self.table)        # index 0
        self.stack.addWidget(self._empty_state) # index 1
        ll.addWidget(self.stack)

        btn_row = QHBoxLayout()
        self.edit_btn = self._mk_btn("✏  " + t("common.edit"), "#f39c12", self._edit, False)
        self.copy_btn = self._mk_btn(t("ui.ink_widget.copy_refill"), "#16a085", self._copy_refill, False)
        self.empty_btn = self._mk_btn(t("ui.ink_widget.mark_empty"), "#8e44ad", self._mark_empty, False)
        self.del_btn  = self._mk_btn("🗑  " + t("common.delete"),   "#e74c3c", self._delete, False)
        btn_row.addWidget(self.edit_btn)
        btn_row.addWidget(self.copy_btn)
        btn_row.addWidget(self.empty_btn)
        btn_row.addWidget(self.del_btn)
        btn_row.addStretch()
        ll.addLayout(btn_row)
        splitter.addWidget(left)

        # Rechte Seite: Details
        self._detail_panel = self._build_detail_panel()
        splitter.addWidget(self._detail_panel)
        splitter.setSizes([650, 380])
        root.addWidget(splitter)

    @staticmethod
    def _mk_btn(text, color, slot, enabled=True):
        b = QPushButton(text)
        b.setEnabled(enabled)
        b.setStyleSheet(f"background:{color};color:white;border:none;padding:6px 12px;border-radius:5px;")
        b.clicked.connect(slot)
        return b

    def _build_detail_panel(self):
        panel = QWidget()
        panel.setStyleSheet("background:white; border-left:1px solid #d5dce6;")
        vl = QVBoxLayout(panel)
        vl.setContentsMargins(16, 16, 16, 16)
        self._detail_title = QLabel(t('ui.ink_widget.tinte_auswahlen_9628463b'))
        self._detail_title.setStyleSheet("font-size:16px;font-weight:bold;color:#1e2a38;")
        vl.addWidget(self._detail_title)
        self._color_preview = QLabel()
        self._color_preview.setFixedHeight(50)
        self._color_preview.setStyleSheet("border-radius:6px; border:1px solid #d5dce6;")
        vl.addWidget(self._color_preview)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameStyle(QFrame.Shape.NoFrame)
        self._dbody = QWidget()
        self._dbl = QVBoxLayout(self._dbody)
        scroll.setWidget(self._dbody)
        vl.addWidget(scroll)
        ph = QLabel(t('ui.ink_widget.tinte_auswahlen_9628463b')); ph.setStyleSheet("color:#95a5a6;font-size:13px;"); ph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._dbl.addWidget(ph); self._dbl.addStretch()
        return panel

    def refresh(self):
        session = get_session()
        try:
            inks = session.query(Ink).order_by(Ink.brand, Ink.name).all()
            cur_id = self._selected_id()
            if not inks:
                self.stack.setCurrentIndex(1)  # EmptyStateWidget
                return
            self.stack.setCurrentIndex(0)      # Tabelle
            self.table.setRowCount(len(inks))
            for row, ink in enumerate(inks):
                color_item = QTableWidgetItem("")
                if ink.color_hex:
                    color_item.setBackground(QColor(ink.color_hex))
                color_item.setData(Qt.ItemDataRole.UserRole, ink.id)
                self.table.setItem(row, 0, color_item)
                self.table.setItem(row, 1, QTableWidgetItem(ink.brand))
                self.table.setItem(row, 2, QTableWidgetItem(ink.name))
                cf = dict(_color_families()).get(ink.color_family or "", ink.color_family or "—")
                self.table.setItem(row, 3, QTableWidgetItem(cf))
                self.table.setItem(row, 4, QTableWidgetItem(t("ui.ink_widget.remaining_empty") if getattr(ink, "is_empty", False) else (f"{ink.remaining_ml:g} ml" if ink.remaining_ml is not None else "—")))
                loads = list(getattr(ink, "ink_loads", []) or [])
                last_loaded = max((l.loaded_date for l in loads if l.loaded_date), default=None)
                self.table.setItem(row, 5, QTableWidgetItem(format_date(last_loaded) if last_loaded else "—"))
                usage = ", ".join(dict(_ink_usage_tags_translated()).get(tag, tag) for tag in _split_csv(getattr(ink, "usage_tags", None)))
                self.table.setItem(row, 6, QTableWidgetItem(usage))
                self.table.setItem(row, 7, QTableWidgetItem(str(getattr(ink, "sheen_level", 0)) if getattr(ink, "has_sheen", False) else ""))
                self.table.setItem(row, 8, QTableWidgetItem("✓" if ink.has_shimmer else ""))
                self.table.setItem(row, 9, QTableWidgetItem(t("common.status.empty") if getattr(ink, "is_empty", False) else (t("common.status.archived") if getattr(ink, "is_archived", False) else t("common.status.active"))))
                if ink.id == cur_id:
                    self.table.selectRow(row)
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
        ink_id = self._selected_id()
        for b in (self.edit_btn, self.copy_btn, self.empty_btn, self.del_btn):
            b.setEnabled(ink_id is not None)
        if ink_id:
            self._show_details(ink_id)

    def _show_details(self, ink_id):
        session = get_session()
        try:
            ink = session.get(Ink, ink_id)
            if not ink: return
            while self._dbl.count():
                i = self._dbl.takeAt(0)
                if i.widget(): i.widget().deleteLater()
            self._detail_title.setText(f"{ink.brand} – {ink.name}")
            if ink.color_hex:
                self._color_preview.setStyleSheet(
                    f"background:{ink.color_hex}; border-radius:6px; border:1px solid #d5dce6;"
                )
            else:
                self._color_preview.setStyleSheet("background:#e0e0e0; border-radius:6px; border:1px solid #d5dce6;")

            def row(lbl, val, color="#2c3e50"):
                w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(0,2,0,2)
                l = QLabel(f"<b>{lbl}</b>"); l.setStyleSheet("color:#7f8c8d; min-width:170px;")
                v = QLabel(str(val) if val else "—"); v.setStyleSheet(f"color:{color};"); v.setWordWrap(True)
                h.addWidget(l); h.addWidget(v, 1); self._dbl.addWidget(w)

            cf = dict(_color_families()).get(ink.color_family or "", ink.color_family or "—")
            row(t("ink.labels.color_family"), cf)
            if ink.color_hex: row(t("ink.labels.hex_color"), ink.color_hex)
            if getattr(ink, "color_type", None): row(t("ink.labels.color_type"), ink.color_type)
            usage_tags = ", ".join(dict(_ink_usage_tags_translated()).get(tag, tag) for tag in _split_csv(getattr(ink, "usage_tags", None)))
            if usage_tags: row(t("ink.labels.usage_rotation"), usage_tags, "#8e44ad")
            if ink.bottle_size_ml: row(t("ink.labels.bottle_size"), f"{ink.bottle_size_ml:g} ml")
            if ink.remaining_ml is not None: row(t("ink.labels.remaining"), f"{ink.remaining_ml:g} ml" + (" · " + t("ink.labels.empty_marker") if getattr(ink, "is_empty", False) else ""), "#e74c3c" if getattr(ink, "is_empty", False) else "#2c3e50")
            stock = ink_stock_rows([ink])[0]
            status_color = {"empty": "#e74c3c", "reorder": "#e67e22", "low": "#f1c40f", "unknown": "#7f8c8d", "ok": "#27ae60"}.get(stock.status, "#2c3e50")
            if stock.fill_pct is not None:
                row(t("ink.labels.fill_level"), f"{stock.fill_pct:.0f}% · {t('enthusiast_lab.status.ink.' + stock.status)}", status_color)
            else:
                row(t("ink.labels.fill_level"), t('enthusiast_lab.status.ink.' + stock.status), status_color)
            row(t("ink.labels.reorder_status"), t('enthusiast_lab.recommendations.ink.' + stock.recommendation), status_color)

            # Reichweite & Kosten-Effizienz (v0.2.68) – nur zeigen, was real belegt ist.
            reach = ink_reach_row(ink)
            reach_color = {"reorder_soon": "#e67e22", "healthy": "#27ae60"}.get(reach.status, "#7f8c8d")
            if reach.estimated_fills_left is not None:
                row(t("ink.labels.reach_fills_left"), f"{reach.estimated_fills_left:g}", reach_color)
            if reach.days_left is not None:
                reach_val = f"{reach.days_left} {t('ink.labels.reach_days_unit')}"
                if reach.projected_empty is not None:
                    reach_val += f" · {t('ink.labels.reach_projected_empty')}: {reach.projected_empty.isoformat()}"
                row(t("ink.labels.reach_days_left"), reach_val, reach_color)
            elif reach.status != "insufficient_data":
                row(t("ink.labels.reach_days_left"), t('enthusiast_lab.reach.status.' + reach.status), reach_color)
            if reach.avg_fill_ml is not None:
                row(t("ink.labels.reach_avg_fill"), f"{reach.avg_fill_ml:g} ml")
            if reach.cost_per_ml is not None:
                cur = reach.currency or ""
                row(t("ink.labels.cost_per_ml"), f"{reach.cost_per_ml:g} {cur}".strip())
            if reach.cost_per_fill is not None:
                cur = reach.currency or ""
                row(t("ink.labels.cost_per_fill"), f"{reach.cost_per_fill:g} {cur}".strip())
            if reach.value_used is not None:
                cur = reach.currency or ""
                row(t("ink.labels.value_used"), f"{reach.value_used:g} {cur}".strip())

            if getattr(ink, "reorder_threshold_ml", None):
                row(t("ink.labels.reorder_threshold"), f"{ink.reorder_threshold_ml:g} ml", status_color)
            if getattr(ink, "reorder_note", None):
                row(t("ink.labels.reorder_note"), ink.reorder_note, "#8e44ad")
            if getattr(ink, "reorder_url", None):
                row(t("ink.labels.reorder_link"), ink.reorder_url, "#2980b9")
            if ink.purchase_price: row(t("ink.labels.purchase_price"), format_money(ink.purchase_price, getattr(ink, "purchase_currency", None)))
            if ink.purchase_date: row(t("ink.labels.purchase_date"), format_date(ink.purchase_date))
            loads_for_last = list(getattr(ink, "ink_loads", []) or [])
            last_loaded = max((l.loaded_date for l in loads_for_last if l.loaded_date), default=None)
            row(t("ink.labels.last_loaded"), format_date(last_loaded) if last_loaded else t("ink.labels.never_loaded"), "#16a085" if last_loaded else "#95a5a6")

            sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine); sep.setStyleSheet("color:#eee; margin:6px 0;")
            self._dbl.addWidget(sep)

            props = []
            if ink.has_shading:  props.append("✓ Shading")
            if ink.has_sheen:    props.append("✓ Sheen")
            if ink.has_shimmer:  props.append("✨ Shimmer")
            if ink.is_pigment:   props.append("🔵 " + t("ink.labels.pigment_ink"))
            if ink.is_waterproof: props.append("💧 " + t("ink.labels.waterproof"))
            if props: row(t("ink.labels.properties"), "  ".join(props), "#3498db")

            row(t("ink.labels.wetness_scale"),          f"{ink.wetness_level} / 5")
            row(t("ink.labels.sheen_level"),        f"{getattr(ink, 'sheen_level', 0)} / 5" + (f" · {ink.sheen_color}" if getattr(ink, 'sheen_color', None) else ""))
            row(t("ink.labels.feathering"),         f"{getattr(ink, 'feathering_level', 2)} / 5")
            row(t("ink.labels.shading"),            f"{getattr(ink, 'shading_level', 3)} / 5")
            row(t("ink.labels.flow"),              f"{getattr(ink, 'flow_level', 3)} / 5")
            row(t("ink.labels.saturation"),          f"{getattr(ink, 'saturation_level', 3)} / 5")
            row(t("ink.labels.cleaning_effort"),  f"{ink.cleaning_effort} / 5")
            if ink.max_days_in_pen:   row(t("ink.labels.max_days_in_pen"), str(ink.max_days_in_pen), "#e74c3c")
            if getattr(ink, "character_notes", None): self._dbl.addWidget(_note_label(f"<b>{t("ink.labels.character")}:</b> {ink.character_notes}"))
            if ink.notes: self._dbl.addWidget(
                _note_label(f"<b>{t("common.notes")}:</b> {ink.notes}")
            )

            # Einsatzstatistik
            times_used = len([l for l in ink.ink_loads])
            row(t("ink.labels.times_used_total"), str(times_used))

            self._dbl.addStretch()
        finally:
            session.close()

    def _context_menu(self, pos):
        row = self.table.rowAt(pos.y())
        if row >= 0:
            self.table.selectRow(row)
            if hasattr(self, "_on_select"):
                self._on_select()
        menu = QMenu(self)
        add = menu.addAction(t('ui.ink_widget.neu_hinzufugen_ab34b5cc'))
        edit = menu.addAction(t('ui.ink_widget.bearbeiten_aed8810b')) if hasattr(self, "_edit") else None
        copy = menu.addAction(t('ui.ink_widget.tinte_kopieren_neues_fass_refill_21aca056')) if hasattr(self, "_copy_refill") else None
        empty = menu.addAction(t('ui.ink_widget.leer_markieren_fbc9fdea')) if hasattr(self, "_mark_empty") else None
        delete = menu.addAction(t('ui.ink_widget.loschen_394b2998')) if hasattr(self, "_delete") else None
        has_selection = self._selected_id() is not None if hasattr(self, "_selected_id") else row >= 0
        if edit: edit.setEnabled(has_selection)
        if copy: copy.setEnabled(has_selection)
        if empty: empty.setEnabled(has_selection)
        if delete: delete.setEnabled(has_selection)
        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if action == add: self._add()
        elif edit and action == edit: self._edit()
        elif copy and action == copy: self._copy_refill()
        elif empty and action == empty: self._mark_empty()
        elif delete and action == delete: self._delete()

    def _add(self):
        dlg = InkDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            session = get_session()
            try:
                session.add(Ink(**dlg.get_data()))
                session.commit()
                AppEventBus.instance().inks_changed.emit()
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, t('ui.ink_widget.fehler_d837361b'), str(e))
            finally:
                session.close()

    def _edit(self):
        ink_id = self._selected_id()
        if not ink_id: return
        session = get_session()
        try:
            ink = session.get(Ink, ink_id)
            if not ink: return
            dlg = InkDialog(self, ink)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                for k, v in dlg.get_data().items():
                    setattr(ink, k, v)
                ink.updated_at = datetime.now()
                session.commit()
                AppEventBus.instance().inks_changed.emit()
                self.refresh()
                self._show_details(ink_id)
        except Exception as e:
            QMessageBox.critical(self, t('ui.ink_widget.fehler_d837361b'), str(e))
        finally:
            session.close()


    def _copy_refill(self):
        """Erstellt aus der gewählten Tinte ein neues Gebinde/Refill.

        Kopiert die Tinteneigenschaften, setzt aber Kaufdatum auf heute,
        Restmenge wieder auf Flaschengröße und lässt Preis/Flaschengröße neu prüfen.
        Dubletten werden anhand Marke + Name + Flaschengröße erkannt.
        """
        ink_id = self._selected_id()
        if not ink_id:
            QMessageBox.information(self, t('ui.ink_widget.tinte_wahlen_75724a04'), t('ui.ink_widget.bitte_zuerst_eine_tinte_auswahlen_80764650'))
            return
        session = get_session()
        try:
            src = session.get(Ink, ink_id)
            if not src:
                return
            clone = Ink(
                brand=src.brand,
                name=src.name,
                color_hex=src.color_hex,
                color_family=src.color_family,
                color_type=getattr(src, "color_type", None),
                bottle_size_ml=src.bottle_size_ml,
                remaining_ml=src.bottle_size_ml or src.remaining_ml,
                purchase_price=None,
                purchase_date=datetime.now(),
                is_empty=False,
                is_archived=False,
                sheen_level=getattr(src, "sheen_level", 0),
                sheen_color=getattr(src, "sheen_color", None),
                feathering_level=getattr(src, "feathering_level", 2),
                shading_level=getattr(src, "shading_level", 3),
                flow_level=getattr(src, "flow_level", 3),
                saturation_level=getattr(src, "saturation_level", 3),
                character_notes=getattr(src, "character_notes", None),
                usage_tags=getattr(src, "usage_tags", None),
                has_shading=src.has_shading,
                has_sheen=src.has_sheen,
                has_shimmer=src.has_shimmer,
                is_pigment=src.is_pigment,
                is_waterproof=src.is_waterproof,
                wetness_level=src.wetness_level,
                cleaning_effort=src.cleaning_effort,
                max_days_in_pen=src.max_days_in_pen,
                notes=src.notes,
                image_path=src.image_path,
            )
            dlg = InkDialog(self, clone)
            dlg.setWindowTitle(t('ui.ink_widget.tinte_kopieren_neues_fass_eintragen_1a76f50f'))
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return
            data = dlg.get_data()
            dup = session.query(Ink).filter(
                Ink.brand == data.get("brand"),
                Ink.name == data.get("name"),
                Ink.bottle_size_ml == data.get("bottle_size_ml"),
                Ink.is_archived == False,
                Ink.is_empty == False,
            ).first()
            if dup and dup.id != ink_id:
                res = QMessageBox.question(
                    self,
                    t('ui.ink_widget.dublettenverdacht_2519361c'),
                    t('ui.ink_widget.es_gibt_bereits_ein_aktives_tintenfass_mit_gleic_a48d9798'),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if res != QMessageBox.StandardButton.Yes:
                    return
            session.add(Ink(**data))
            session.commit()
            AppEventBus.instance().inks_changed.emit()
            self.refresh()
            QMessageBox.information(self, t('ui.ink_widget.refill_angelegt_b77e2392'), t('ui.ink_widget.neues_tintenfass_wurde_angelegt_preis_und_fullgr_6ea6d8ce'))
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, t('ui.ink_widget.fehler_d837361b'), str(e))
        finally:
            session.close()

    def _mark_empty(self):
        ink_id = self._selected_id()
        if not ink_id: return
        session = get_session()
        try:
            ink = session.get(Ink, ink_id)
            if not ink: return
            ink.is_empty = True
            ink.remaining_ml = 0
            ink.updated_at = datetime.now()
            session.commit()
            AppEventBus.instance().inks_changed.emit()
            self.refresh(); self._show_details(ink_id)
        finally:
            session.close()

    def _delete(self):
        ink_id = self._selected_id()
        if not ink_id: return
        session = get_session()
        try:
            ink = session.get(Ink, ink_id)
            if not ink: return
            if ink.ink_loads:
                # Historie behalten: benutzt gewesene Tinten werden archiviert statt hart gelöscht.
                if QMessageBox.question(self, t('ui.ink_widget.archivieren_b96bf488'), t('ui.ink_widget.diese_tinte_wurde_bereits_verwendet_statt_losche_c63aabb3'), QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                    ink.is_empty = True
                    ink.is_archived = True
                    ink.remaining_ml = 0
                    session.commit(); self.refresh()
                return
            if QMessageBox.question(
                self, t('ui.ink_widget.loschen_068c5fde'), t('ui.ink_widget.confirm_delete_ink', ink=f"{ink.brand} {ink.name}"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            ) == QMessageBox.StandardButton.Yes:
                session.delete(ink)
                session.commit()
                AppEventBus.instance().inks_changed.emit()
                self.refresh()
        finally:
            session.close()


    def _import_inks(self):
        path, _ = QFileDialog.getOpenFileName(self, t('ui.ink_widget.tintendaten_importieren_670b8bf8'), "", t('ui.ink_widget.csv_dateien_csv_f55ca42b'))
        if not path:
            return
        session = get_session()
        added = updated = skipped = 0
        errors = []
        def to_float(v):
            try:
                return float(str(v).replace(",", ".")) if str(v).strip() else None
            except Exception:
                return None
        def to_int(v, default=None):
            try:
                return int(float(str(v).replace(",", "."))) if str(v).strip() else default
            except Exception:
                return default
        def to_bool(v):
            return str(v).strip().lower() in ("1", "true", "yes", "ja", "x", "✓")
        def to_date(v):
            if not v or not str(v).strip():
                return None
            s = str(v).strip()
            for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%m/%d/%Y", "%Y/%m/%d",
                        "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"):
                try:
                    return datetime.strptime(s, fmt)
                except ValueError:
                    continue
            return None
        try:
            # ── Schritt 1: Validierungsdurchlauf ─────────────────────────
            preview_results = []
            raw_rows = []
            with open(path, newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for n, row in enumerate(reader, start=2):
                    brand = (row.get("brand") or row.get("Marke") or "").strip()
                    name  = (row.get("name")  or row.get("Name")  or "").strip()
                    if not brand or not name:
                        preview_results.append({"line": n, "label": f"Zeile {n}", "status": "error", "msg": "Marke oder Name fehlt"})
                        continue
                    date_raw = row.get("purchase_date") or row.get("Kaufdatum") or ""
                    date_val = to_date(date_raw)
                    date_msg = f"Kaufdatum unbekannt: '{date_raw}' → wird ignoriert" if (date_raw and not date_val) else ""
                    status = "warn" if date_msg else "ok"
                    preview_results.append({"line": n, "label": f"{brand} – {name}", "status": status, "msg": date_msg or "OK"})
                    raw_rows.append((n, row))

            if not preview_results:
                QMessageBox.information(self, t('ui.ink_widget.import_4c42d4fa'), t('ui.ink_widget.keine_gultigen_zeilen_in_der_csv_datei_gefunden_39c1d45a'))
                return

            # ── Schritt 2: Vorschau anzeigen ─────────────────────────────
            dlg = ImportPreviewDialog(preview_results, "Tinten-Import Vorschau", self)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return

            importable_lines = {r["line"] for r in preview_results if r["status"] in ("ok", "warn")}

            # ── Schritt 3: Importieren ────────────────────────────────────
            with open(path, newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for n, row in enumerate(reader, start=2):
                    if n not in importable_lines:
                        skipped += 1
                        continue
                    try:
                        brand = (row.get("brand") or row.get("Marke") or "").strip()
                        name = (row.get("name") or row.get("Name") or "").strip()
                        bottle = to_float(row.get("bottle_size_ml") or row.get("Flaschengröße") or row.get("Fassgröße"))
                        ink = session.query(Ink).filter(Ink.brand == brand, Ink.name == name, Ink.bottle_size_ml == bottle).first()
                        data = dict(
                            brand=brand,
                            name=name,
                            bottle_size_ml=bottle,
                            color_hex=(row.get("color_hex") or row.get("Hex") or "").strip() or None,
                            color_family=normalize_color_family(row.get("color_family") or row.get("Farbfamilie") or ""),
                            color_type=(row.get("color_type") or row.get("Farbtyp") or "").strip() or None,
                            remaining_ml=to_float(row.get("remaining_ml") or row.get("Rest")),
                            purchase_price=to_float(row.get("purchase_price") or row.get("Kaufpreis")),
                            purchase_currency=(row.get("purchase_currency") or row.get("Kaufpreis-Währung") or LocaleService.instance().currency).strip()[:3].upper() or None,
                            is_empty=to_bool(row.get("is_empty") or row.get("Leer") or ""),
                            is_archived=to_bool(row.get("is_archived") or row.get("Archiv") or ""),
                            wetness_level=to_int(row.get("wetness_level") or row.get("Nässe"), 3),
                            sheen_level=to_int(row.get("sheen_level") or row.get("Sheen"), 0),
                            sheen_color=(row.get("sheen_color") or "").strip() or None,
                            has_sheen=to_bool(row.get("has_sheen") or row.get("Sheen vorhanden") or ""),
                            has_shimmer=to_bool(row.get("has_shimmer") or row.get("Schimmer") or ""),
                            feathering_level=to_int(row.get("feathering_level") or row.get("Feathering"), 2),
                            shading_level=to_int(row.get("shading_level") or row.get("Shading"), 3),
                            flow_level=to_int(row.get("flow_level") or row.get("Fluss"), 3),
                            saturation_level=to_int(row.get("saturation_level") or row.get("Sättigung"), 3),
                            cleaning_effort=to_int(row.get("cleaning_effort") or row.get("Reinigung"), 3),
                            max_days_in_pen=to_int(row.get("max_days_in_pen") or row.get("Max Tage"), None),
                            usage_tags=(row.get("usage_tags") or row.get("Einsatz") or row.get("Themen") or "").strip() or None,
                            notes=(row.get("notes") or row.get("Bemerkungen") or "").strip() or None,
                            character_notes=(row.get("character_notes") or row.get("Charakter") or "").strip() or None,
                            purchase_date=to_date(row.get("purchase_date") or row.get("Kaufdatum")),
                        )
                        if ink:
                            for k, v in data.items(): setattr(ink, k, v)
                            ink.updated_at = datetime.now(); updated += 1
                        else:
                            session.add(Ink(**data)); added += 1
                    except Exception as e:
                        errors.append(f"Zeile {n}: {e}")
            session.commit()
            AppEventBus.instance().inks_changed.emit()
            msg = t("ui.ink_widget.import_done", added=added, updated=updated, skipped=skipped)
            if errors:
                msg += t("ui.ink_widget.import_errors", errors="\n".join(errors[:20]))
            QMessageBox.information(self, t('ui.ink_widget.import_4c42d4fa'), msg)
            self.refresh()
        except Exception as e:
            session.rollback(); QMessageBox.critical(self, t('ui.ink_widget.importfehler_f1874112'), str(e))
        finally:
            session.close()

    def _export_inks(self):
        path, _ = QFileDialog.getSaveFileName(self, t('ui.ink_widget.tintendaten_exportieren_1f27a8fb'), "tinten_export.csv", t('ui.ink_widget.csv_dateien_csv_f55ca42b'))
        if not path:
            return
        session = get_session()
        try:
            inks = session.query(Ink).order_by(Ink.brand, Ink.name).all()
            cols = [
                "id", "brand", "name", "color_type", "color_family", "color_hex",
                "bottle_size_ml", "remaining_ml", "is_empty", "is_archived",
                "purchase_price", "purchase_currency", "purchase_date", "last_loaded_date",
                "wetness_level", "sheen_level", "sheen_color", "has_sheen", "has_shimmer",
                "feathering_level", "shading_level", "flow_level", "saturation_level",
                "cleaning_effort", "max_days_in_pen", "usage_tags", "notes", "character_notes"
            ]
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(cols)
                for ink in inks:
                    loads = list(getattr(ink, "ink_loads", []) or [])
                    last = max((l.loaded_date for l in loads if l.loaded_date), default=None)
                    writer.writerow([
                        ink.id, ink.brand, ink.name, getattr(ink, "color_type", None), ink.color_family, ink.color_hex,
                        ink.bottle_size_ml, ink.remaining_ml, getattr(ink, "is_empty", False), getattr(ink, "is_archived", False),
                        ink.purchase_price, getattr(ink, "purchase_currency", None), ink.purchase_date, last,
                        ink.wetness_level, getattr(ink, "sheen_level", 0), getattr(ink, "sheen_color", None), ink.has_sheen, ink.has_shimmer,
                        getattr(ink, "feathering_level", None), getattr(ink, "shading_level", None), getattr(ink, "flow_level", None), getattr(ink, "saturation_level", None),
                        ink.cleaning_effort, ink.max_days_in_pen, getattr(ink, "usage_tags", None), ink.notes, getattr(ink, "character_notes", None)
                    ])
            QMessageBox.information(self, t('ui.ink_widget.export_9fd0dd51'), t('ui.ink_widget.exported_ink_data', path=path))
        except Exception as e:
            QMessageBox.critical(self, t('ui.ink_widget.exportfehler_dc662f4e'), str(e))
        finally:
            session.close()


def _note_label(text):
    lbl = QLabel(text); lbl.setStyleSheet("color:#555; font-size:12px; padding:4px 0;"); lbl.setWordWrap(True)
    return lbl


class InkDialog(QDialog):
    def __init__(self, parent=None, ink: Optional[Ink] = None):
        super().__init__(parent)
        self.ink = ink
        self.setWindowTitle(t("ink.edit_title") if ink else t("ink.add"))
        self.setMinimumWidth(scale_px(560))
        self.setMinimumHeight(scale_px(600))
        self._setup_ui()
        if ink: self._load()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameStyle(QFrame.Shape.NoFrame)
        content = QWidget(); cl = QVBoxLayout(content); cl.setSpacing(12); scroll.setWidget(content)

        # Grunddaten
        g1 = QGroupBox(t('ui.ink_widget.grundinformationen_9bbfb616')); f1 = QFormLayout(g1)
        self.brand_edit = QLineEdit(); self.brand_edit.setPlaceholderText(t('ui.ink_widget.z_b_diamine_sailor_pilot_b39b6086'))
        self.name_edit  = QLineEdit(); self.name_edit.setPlaceholderText(t('ui.ink_widget.z_b_oxblood_wapiti_iroshizuku_ed96a8c2'))
        self.hex_edit   = QLineEdit(); self.hex_edit.setPlaceholderText(t('ui.ink_widget.rrggbb_z_b_1a2b3c_b5ae2d5c'))
        self.color_type_edit = QLineEdit(); self.color_type_edit.setPlaceholderText(t('ui.ink_widget.z_b_sheen_monster_kuhles_grau_petrolgrun_6e8d9344'))
        self.cf_combo   = QComboBox()
        for val, lbl in _color_families():
            self.cf_combo.addItem(lbl, val)
        f1.addRow(t('ui.ink_widget.marke_e123b4a6'),      self.brand_edit)
        f1.addRow(t('ui.ink_widget.name_a4bf0792'),       self.name_edit)
        f1.addRow(t('ui.ink_widget.farbe_hex_9e1be064'),  self.hex_edit)
        f1.addRow(t('ui.ink_widget.farbtyp_813d69ea'),      self.color_type_edit)
        f1.addRow(t('ui.ink_widget.farbfamilie_af08f17e'),  self.cf_combo)
        cl.addWidget(g1)

        # Kauf
        g2 = QGroupBox(t('ui.ink_widget.kauf_3ba87130')); f2 = QFormLayout(g2)
        self.date_edit    = QDateEdit(QDate.currentDate()); self.date_edit.setCalendarPopup(True); self.date_edit.setDisplayFormat(LocaleService.instance().qt_date_format)
        default_cur = LocaleService.instance().currency
        self.price_spin   = QDoubleSpinBox(); self.price_spin.setRange(0,999); self.price_spin.setSuffix(f" {default_cur}"); self.price_spin.setDecimals(2)
        self.price_currency_combo = QComboBox(); self.price_currency_combo.addItems([t('ui.ink_widget.chf_e79d52f9'), t('ui.ink_widget.eur_3c1feb77'), t('ui.ink_widget.usd_df729bfc'), t('ui.ink_widget.gbp_a19c745e')]); self.price_currency_combo.setCurrentText(default_cur)
        self.bottle_spin  = QDoubleSpinBox(); self.bottle_spin.setRange(0,1000); self.bottle_spin.setSuffix(" ml"); self.bottle_spin.setDecimals(1)
        self.remain_spin  = QDoubleSpinBox(); self.remain_spin.setRange(0,1000); self.remain_spin.setSuffix(" ml"); self.remain_spin.setDecimals(1)
        self.empty_cb = QCheckBox(t('ui.ink_widget.tintenfass_ist_leer_nicht_mehr_vorschlagen_b2225d07'))
        f2.addRow(t('ui.ink_widget.kaufdatum_471e8f67'),       self.date_edit)
        f2.addRow(t('ui.ink_widget.kaufpreis_18bc5dd6'),       self.price_spin)
        f2.addRow(t('ui.ink_widget.wahrung_50dfe63c'),         self.price_currency_combo)
        f2.addRow(t('ui.ink_widget.flaschengroe_b7ce4d6e'),   self.bottle_spin)
        f2.addRow(t('ui.ink_widget.restmenge_4162cd96'),       self.remain_spin)
        f2.addRow(t('ui.ink_widget.leer_002e1a27'),            self.empty_cb)
        cl.addWidget(g2)

        # Eigenschaften
        g3 = QGroupBox(t('ui.ink_widget.eigenschaften_5bbb30c1')); hl3 = QHBoxLayout(g3)
        self.shading_cb  = QCheckBox(t('ui.ink_widget.shading_c9458329'))
        self.sheen_cb    = QCheckBox(t('ui.ink_widget.sheen_acf03a5a'))
        self.shimmer_cb  = QCheckBox(t('ui.ink_widget.shimmer_42988307'))
        self.pigment_cb  = QCheckBox(t('ui.ink_widget.pigment_39d6b60b'))
        self.waterproof_cb = QCheckBox(t('ui.ink_widget.wasserfest_19e8db26'))
        for cb in (self.shading_cb, self.sheen_cb, self.shimmer_cb, self.pigment_cb, self.waterproof_cb):
            hl3.addWidget(cb)
        cl.addWidget(g3)

        # Einsatz-Tags für Rotation/Rolle/Thema
        g_usage = QGroupBox(t("rotation.role_group"))
        usage_v = QVBoxLayout(g_usage)
        self.usage_tag_cbs = {}
        row_layouts = [QHBoxLayout(), QHBoxLayout(), QHBoxLayout()]
        for idx, (tag, label) in enumerate(_ink_usage_tags_translated()):
            cb = QCheckBox(label)
            self.usage_tag_cbs[tag] = cb
            row_layouts[min(idx // 7, 2)].addWidget(cb)
        for rl in row_layouts:
            rl.addStretch(1)
            usage_v.addLayout(rl)
        cl.addWidget(g_usage)

        # Skalen
        g4 = QGroupBox(t('ui.ink_widget.skalen_2a50b1ef')); f4 = QFormLayout(g4)
        self.wet_spin   = QSpinBox(); self.wet_spin.setRange(1,5); self.wet_spin.setSuffix(t('ui.ink_widget.1_trocken_5_sehr_nass_ec64f773'))
        self.clean_spin = QSpinBox(); self.clean_spin.setRange(1,5); self.clean_spin.setSuffix(t('ui.ink_widget.1_einfach_5_aufwandig_4ea0cbfe'))
        self.sheen_level_spin = QSpinBox(); self.sheen_level_spin.setRange(0,5); self.sheen_level_spin.setSuffix(" / 5")
        self.sheen_color_edit = QLineEdit(); self.sheen_color_edit.setPlaceholderText(t('ui.ink_widget.z_b_rot_gold_046473ba'))
        self.feather_spin = QSpinBox(); self.feather_spin.setRange(1,5); self.feather_spin.setSuffix(" / 5")
        self.shading_spin = QSpinBox(); self.shading_spin.setRange(1,5); self.shading_spin.setSuffix(" / 5")
        self.flow_spin = QSpinBox(); self.flow_spin.setRange(1,5); self.flow_spin.setSuffix(" / 5")
        self.saturation_spin = QSpinBox(); self.saturation_spin.setRange(1,5); self.saturation_spin.setSuffix(" / 5")
        self.max_days_spin = QSpinBox(); self.max_days_spin.setRange(0,365); self.max_days_spin.setSpecialValueText(t("common.no_limit")); self.max_days_spin.setSuffix(t('ui.ink_widget.tage_b58144c7'))
        f4.addRow(t('ui.ink_widget.nassskala_9822d6c3'),          self.wet_spin)
        f4.addRow(t('ui.ink_widget.sheen_level_09a2c679'),        self.sheen_level_spin)
        f4.addRow(t('ui.ink_widget.sheen_farbe_2619a999'),        self.sheen_color_edit)
        f4.addRow(t('ui.ink_widget.feathering_126d8d58'),         self.feather_spin)
        f4.addRow(t('ui.ink_widget.shading_c9458329'),            self.shading_spin)
        f4.addRow(t('ui.ink_widget.fluss_beeb6e7f'),              self.flow_spin)
        f4.addRow(t('ui.ink_widget.sattigung_1fa1662f'),          self.saturation_spin)
        f4.addRow(t('ui.ink_widget.reinigungsaufwand_547719cc'),  self.clean_spin)
        f4.addRow(t('ui.ink_widget.max_tage_im_fuller_678d3ba8'), self.max_days_spin)
        cl.addWidget(g4)

        # Notizen
        g5 = QGroupBox(t('ui.ink_widget.notizen_e5147bb7')); fl5 = QFormLayout(g5)
        self.character_edit = QTextEdit(); self.character_edit.setMaximumHeight(70); self.character_edit.setPlaceholderText(t('ui.ink_widget.charakter_bemerkung_z_b_ideal_fur_ef_burotauglic_7e2d5887'))
        self.notes_edit = QTextEdit(); self.notes_edit.setMaximumHeight(80)
        fl5.addRow(t('ui.ink_widget.charakter_fd98cec2'), self.character_edit)
        fl5.addRow(t('ui.ink_widget.notizen_e5147bb7'), self.notes_edit)
        cl.addWidget(g5)

        root.addWidget(scroll)

        br = QHBoxLayout(); br.addStretch()
        cancel = QPushButton(t('ui.ink_widget.abbrechen_049af5c4')); cancel.setStyleSheet(BTN_MUTED)
        cancel.clicked.connect(self.reject)
        save = QPushButton(t('ui.ink_widget.speichern_1bd284ab')); save.setStyleSheet(BTN_SUCCESS)
        save.clicked.connect(self._save)
        br.addWidget(cancel); br.addWidget(save); root.addLayout(br)

    def _load(self):
        i = self.ink
        self.brand_edit.setText(i.brand or "")
        self.name_edit.setText(i.name or "")
        self.hex_edit.setText(i.color_hex or "")
        self.color_type_edit.setText(getattr(i, "color_type", None) or "")
        for idx, (val, _) in enumerate(_color_families()):
            if val == i.color_family: self.cf_combo.setCurrentIndex(idx); break
        if i.purchase_date:
            d = i.purchase_date; self.date_edit.setDate(QDate(d.year, d.month, d.day))
        self.price_spin.setValue(i.purchase_price or 0)
        self.price_currency_combo.setCurrentText(getattr(i, "purchase_currency", None) or LocaleService.instance().currency)
        self.bottle_spin.setValue(i.bottle_size_ml or 0)
        self.remain_spin.setValue(i.remaining_ml or 0)
        self.empty_cb.setChecked(bool(getattr(i, "is_empty", False)))
        self.shading_cb.setChecked(i.has_shading)
        self.sheen_cb.setChecked(i.has_sheen)
        self.shimmer_cb.setChecked(i.has_shimmer)
        self.pigment_cb.setChecked(i.is_pigment)
        self.waterproof_cb.setChecked(i.is_waterproof)
        for tag in _split_csv(getattr(i, "usage_tags", None)):
            if tag in self.usage_tag_cbs:
                self.usage_tag_cbs[tag].setChecked(True)
        self.wet_spin.setValue(i.wetness_level)
        self.clean_spin.setValue(i.cleaning_effort)
        self.sheen_level_spin.setValue(getattr(i, "sheen_level", 0) or 0)
        self.sheen_color_edit.setText(getattr(i, "sheen_color", None) or "")
        self.feather_spin.setValue(getattr(i, "feathering_level", 2) or 2)
        self.shading_spin.setValue(getattr(i, "shading_level", 3) or 3)
        self.flow_spin.setValue(getattr(i, "flow_level", 3) or 3)
        self.saturation_spin.setValue(getattr(i, "saturation_level", 3) or 3)
        self.max_days_spin.setValue(i.max_days_in_pen or 0)
        self.character_edit.setPlainText(getattr(i, "character_notes", None) or "")
        self.notes_edit.setPlainText(i.notes or "")

    def _save(self):
        if not self.brand_edit.text().strip():
            QMessageBox.warning(self, t('ui.ink_widget.pflichtfeld_1448c986'), t('ui.ink_widget.bitte_marke_eingeben_7bcc7efe')); return
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, t('ui.ink_widget.pflichtfeld_1448c986'), t('ui.ink_widget.bitte_name_eingeben_b4f74f0a')); return
        self.accept()

    def get_data(self) -> dict:
        d = self.date_edit.date()
        return {
            "brand": self.brand_edit.text().strip(),
            "name":  self.name_edit.text().strip(),
            "color_hex":    self.hex_edit.text().strip() or None,
            "color_family": self.cf_combo.currentData(),
            "color_type": self.color_type_edit.text().strip() or None,
            "purchase_date": datetime(d.year(), d.month(), d.day()),
            "purchase_price": self.price_spin.value() or None,
            "purchase_currency": self.price_currency_combo.currentText(),
            "bottle_size_ml": self.bottle_spin.value() or None,
            "remaining_ml":   0 if self.empty_cb.isChecked() else (self.remain_spin.value() or None),
            "is_empty": self.empty_cb.isChecked(),
            "has_shading":    self.shading_cb.isChecked(),
            "has_sheen":      self.sheen_cb.isChecked(),
            "has_shimmer":    self.shimmer_cb.isChecked(),
            "is_pigment":     self.pigment_cb.isChecked(),
            "is_waterproof":  self.waterproof_cb.isChecked(),
            "wetness_level":  self.wet_spin.value(),
            "sheen_level": self.sheen_level_spin.value(),
            "sheen_color": self.sheen_color_edit.text().strip() or None,
            "feathering_level": self.feather_spin.value(),
            "shading_level": self.shading_spin.value(),
            "flow_level": self.flow_spin.value(),
            "saturation_level": self.saturation_spin.value(),
            "cleaning_effort": self.clean_spin.value(),
            "max_days_in_pen": self.max_days_spin.value() or None,
            "usage_tags": ",".join(tag for tag, cb in self.usage_tag_cbs.items() if cb.isChecked()) or None,
            "character_notes": self.character_edit.toPlainText().strip() or None,
            "notes": self.notes_edit.toPlainText().strip() or None,
        }
