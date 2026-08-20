"""Füller-Dialoge (v0.3.02, aus ui/pen_widget.py ausgelagert).

Enthält ServiceHelpDialog, SizeCompareDialog, ServiceBlockDialog,
PenDialog und LoadInkDialog. Datenzugriffe laufen über die Repository-/
Service-Schicht; ui/pen_widget re-exportiert die Klassen, sodass
bestehende Importe (`from ui.pen_widget import PenDialog`) stabil bleiben.
"""
from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (QInputDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QLineEdit, QDialog, QFormLayout,
                               QComboBox, QDateEdit, QTextEdit, QCheckBox,
                               QGroupBox, QScrollArea, QMessageBox,
                               QSpinBox, QTabWidget, QFileDialog)
from PySide6.QtCore import Qt, QDate, QRectF, QPointF
from PySide6.QtGui import QColor, QFont, QPixmap, QPainter, QPen, QBrush, QPolygonF

from database.db import get_session, _data_dir
from database.models import Pen, Ink, Nib
from database.repositories import InkRepository, NibRepository, PenRepository
from i18n.translator import LocaleService, t
from logic.event_bus import AppEventBus
from logic.image_url_security import _is_safe_remote_image_url
from logic.media_storage_service import download_image_bytes
from logic.rule_engine import RuleEngine, LEVEL_ICONS
from logic.rotation_engine import RotationEngine
from ui.common import ResponsiveDialog
from ui.localized_inputs import LocalizedDoubleSpinBox
from ui.locale_widgets import (
    bind_currency_combo,
    populate_currency_combo,
    set_combo_currency,
)
from ui.ink_widget import InkDialog
from ui.nib_widget import NibDialog
from ui.role_prefs_dialog import RolePrefsDialog
from ui.pen_common import (TAG_KEYS, _fill_system_label,
                           _fill_systems, _rotation_roles, _rotation_themes, _tag_label)
from ui.theme import BTN_MUTED, BTN_SUCCESS
from ui.ui_scale import scale_px


# v0.3.02-Audit-Fix F-01: Beim Datei-Split verlorenes Hilfetext-Dict
# wiederhergestellt (bewusst dreisprachig hartcodiert, wie seit v0.2.x).
SERVICE_HELP = {'de': {'piston': 'Kolbenfüller: Vor Service entleeren, mit lauwarmem Wasser spülen. Keine Gewalt am Kolbenknopf. Bei schwergängigem Kolben: nicht weiterdrehen, Service eintragen.', 'vac': 'Vac-Füller: Keine Shimmer-/Pigmenttinte für lange Standzeiten. Mehrfach spülen, Dichtung prüfen. Bei kratzigem Hub oder Leck: sperren und Service planen.', 'converter': 'Converter: Converter herausnehmen, separat spülen. Ideal für schnelle Reinigung und Tintenwechsel. Defekte Converter können günstig ersetzt werden.', 'cartridge': 'Patrone: Patrone entfernen, Griffstück spülen. Alte Patronen nicht lange offen lagern. Bei Startproblemen Feed wässern.', 'eyedropper': 'Eyedropper: Vor dem Öffnen vollständig entleeren. Gewinde/Dichtung prüfen und vorsichtig fetten. Shimmer kann sedimentieren – regelmäßig bewegen und reinigen.'}, 'en': {'piston': 'Piston filler: empty before service and flush with lukewarm water. Do not force the piston knob. If it feels stuck, block the pen and schedule service.', 'vac': 'Vac filler: avoid shimmer/pigment inks for long rotations. Flush thoroughly and check seals. Block the pen if the plunger feels rough or leaks.', 'converter': 'Converter: remove and flush separately. Best for easy cleaning and frequent ink changes. Faulty converters are usually easy to replace.', 'cartridge': 'Cartridge: remove cartridge and flush the section. Do not store opened cartridges for too long. Soak the feed if the pen has hard starts.', 'eyedropper': 'Eyedropper: empty fully before opening. Check seals/threads and grease carefully. Shimmer may settle, so move and clean regularly.'}, 'fr': {'piston': 'Stylo à piston : vider avant service et rincer à l’eau tiède. Ne pas forcer le bouton du piston. Si le mécanisme bloque, mettre le stylo en service.', 'vac': 'Vac filler : éviter les encres shimmer/pigmentées en longue rotation. Rincer soigneusement et contrôler les joints. Bloquer en cas de fuite ou de piston rugueux.', 'converter': 'Convertisseur : retirer et rincer séparément. Très pratique pour les changements d’encre. Un convertisseur défectueux se remplace facilement.', 'cartridge': 'Cartouche : retirer la cartouche et rincer la section. Ne pas garder les cartouches ouvertes trop longtemps. Tremper le feed en cas de démarrage difficile.', 'eyedropper': 'Eyedropper : vider complètement avant ouverture. Vérifier les joints/filetages et graisser prudemment. Le shimmer peut se déposer : nettoyer régulièrement.'}}


class ServiceHelpDialog(ResponsiveDialog):

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
        self.enable_responsive_layout(
            700, 520, minimum_width=340, minimum_height=280,
            scroll=True
        )

    def _refresh(self):
        lang = self.lang_combo.currentData()
        fs = self.fs_combo.currentData()
        title = self.fs_combo.currentText()
        body = SERVICE_HELP.get(lang, SERVICE_HELP['de']).get(fs, '')
        footer = t('ui.pen_widget.service_help_footer')
        self.text.setHtml(f'<h2>{title}</h2><p>{body}</p><hr><p>{footer}</p>')

class SizeCompareDialog(ResponsiveDialog):

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
        self.enable_responsive_layout(
            1040, 720, minimum_width=420, minimum_height=320,
            scroll=True
        )

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
            pens = PenRepository(session).all_sorted()
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

class ServiceBlockDialog(ResponsiveDialog):
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
        self.cost_spin = LocalizedDoubleSpinBox()
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
        hint.setStyleSheet('color:#5f6f72; padding:6px;')
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
        self.enable_responsive_layout(
            760, 620, minimum_width=360, minimum_height=320,
            scroll=True
        )

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
        return {'status': self.status_combo.currentData(), 'start': start, 'end': end, 'days': days, 'cost': self.cost_spin.value(), 'currency': self.cost_currency_combo.currentText(), 'notes': self.notes_edit.toPlainText().strip() or None}

class PenDialog(ResponsiveDialog):
    """Dialog zum Anlegen/Bearbeiten eines Füllers."""

    def __init__(self, parent=None, pen: Optional[Pen]=None):
        super().__init__(parent)
        self.pen = pen
        self._initial_state = None
        self.setWindowTitle(t('pen.edit_title') if pen else t('pen.add'))
        self.setMinimumSize(scale_px(720), scale_px(600))
        self._setup_ui()
        if pen:
            self._load()
        self._initial_state = self._state_signature()
        self.enable_responsive_layout(
            900, 740, minimum_width=380, minimum_height=320,
            scroll=True
        )

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
        self.price_spin = LocalizedDoubleSpinBox()
        self.price_spin.setRange(0, 99999)
        self.price_spin.setDecimals(2)
        self.market_spin = LocalizedDoubleSpinBox()
        self.market_spin.setRange(0, 99999)
        self.market_spin.setDecimals(2)
        self.insur_spin = LocalizedDoubleSpinBox()
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
        self.len_spin = LocalizedDoubleSpinBox()
        self.len_spin.setRange(0, 500)
        self.len_spin.setSuffix(' mm')
        self.uncapped_spin = LocalizedDoubleSpinBox()
        self.uncapped_spin.setRange(0, 500)
        self.uncapped_spin.setSuffix(' mm')
        self.posted_spin = LocalizedDoubleSpinBox()
        self.posted_spin.setRange(0, 500)
        self.posted_spin.setSuffix(' mm')
        self.dia_spin = LocalizedDoubleSpinBox()
        self.dia_spin.setRange(0, 100)
        self.dia_spin.setSuffix(' mm')
        self.section_dia_spin = LocalizedDoubleSpinBox()
        self.section_dia_spin.setRange(0, 100)
        self.section_dia_spin.setSuffix(' mm')
        self.wt_spin = LocalizedDoubleSpinBox()
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
        self.capacity_spin = LocalizedDoubleSpinBox()
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
        """Compatibility helper using the same secured path as active imports."""
        raw = (url or '').strip()
        if not _is_safe_remote_image_url(raw):
            return None
        img_dir = _data_dir() / 'images' / 'pens'
        img_dir.mkdir(parents=True, exist_ok=True)
        try:
            data, suffix = download_image_bytes(raw, timeout_s=12)
            target = img_dir / f'{self._safe_image_basename()}{suffix}'
            target.write_bytes(data)
            return str(target)
        except (OSError, ValueError):
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
            for n in NibRepository(session).all_sorted():
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

        # v0.2.87: Die ersten ZWEI Stufen öffnen (vorher nur eine).
        # Maße: KI-Prompt + Herstellerseite. Bilder: Hersteller + KI.
        # Vorher blieb die jeweils zweite - fachlich wichtigste - Stufe
        # unsichtbar, obwohl sie gebaut wurde.
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
        set_combo_currency(self.market_currency_combo, getattr(p, 'market_currency', None) or getattr(p, 'purchase_currency', None))
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

    def _state_signature(self) -> tuple[dict, dict, dict]:
        """Vergleichbarer Dialogzustand für den Schutz ungespeicherter Eingaben."""
        return (self.get_data(), self.get_inline_nib_data(), self.get_nib_setup_data())

    def _has_unsaved_changes(self) -> bool:
        return self._initial_state is not None and self._state_signature() != self._initial_state

    def reject(self) -> None:
        """Verhindert versehentlichen Datenverlust durch Abbrechen oder Fenster-X."""
        if self.isVisible() and self._has_unsaved_changes():
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Icon.Warning)
            box.setWindowTitle(t('pen.unsaved_title'))
            box.setText(t('pen.unsaved_body'))
            keep_button = box.addButton(
                t('pen.keep_editing'), QMessageBox.ButtonRole.RejectRole
            )
            discard_button = box.addButton(
                t('pen.discard_changes'), QMessageBox.ButtonRole.DestructiveRole
            )
            box.setDefaultButton(keep_button)
            box.exec()
            if box.clickedButton() is not discard_button:
                return
        super().reject()

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
        return {'brand': self.brand_edit.text().strip(), 'model': self.model_edit.text().strip(), 'color': self.color_edit.text().strip() or None, 'fill_system': self.fs_combo.currentData(), 'nib_id': self.nib_combo.currentData(), 'compatible_nibs': self.compat_edit.toPlainText().strip() or None, 'incompatible_nibs': self.incompat_edit.toPlainText().strip() or None, 'purchase_date': datetime(d.year(), d.month(), d.day()), 'purchase_price': self.price_spin.value() or None, 'purchase_currency': self.price_currency_combo.currentText(), 'current_market_value': self.market_spin.value() or None, 'market_currency': self.market_currency_combo.currentText(), 'insurance_value': self.insur_spin.value() or None, 'insurance_currency': self.insurance_currency_combo.currentText(), 'length_mm': self.len_spin.value() or None, 'length_uncapped_mm': self.uncapped_spin.value() or None, 'length_posted_mm': self.posted_spin.value() or None, 'diameter_mm': self.dia_spin.value() or None, 'section_diameter_mm': self.section_dia_spin.value() or None, 'weight_g': self.wt_spin.value() or None, 'image_path': self._prepare_image_path(), 'ink_capacity_ml': self.capacity_spin.value() or None, 'popularity_rating': self.pop_spin.value(), 'must_include_in_rotation': self.must_rotation_cb.isChecked(), 'rotation_role': self.role_combo.currentData() or 'writer', 'rotation_theme': self.theme_combo.currentData(), 'tags': ','.join(tags) or None, 'writing_feel_notes': self.feel_edit.toPlainText().strip() or None, 'problem_notes': self.problem_edit.toPlainText().strip() or None, 'cleaning_notes': self.clean_edit.toPlainText().strip() or None}

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

class LoadInkDialog(ResponsiveDialog):
    """Dialog zum Einfüllen einer Tinte mit Regelprüfung."""

    def __init__(self, parent=None, pen_id: int=None):
        super().__init__(parent)
        self.pen_id = pen_id
        self.setWindowTitle(t('ui.pen_widget.tinte_einfullen_4b5d3bbe'))
        self.setMinimumWidth(520)
        self._setup_ui()
        self.enable_responsive_layout(
            680, 560, minimum_width=340, minimum_height=280,
            scroll=True
        )

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
            inks = InkRepository(session).usable_sorted()
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
            self.volume_spin = LocalizedDoubleSpinBox()
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
            inks = InkRepository(session).usable_sorted()
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
                    override_reason = reason.strip() or t('ui.pen_widget.override_reason_default')
        finally:
            session.close()
        ok, msg = RotationEngine().fill_pen(self.pen_id, ink_id, override_reason=override_reason, source='manual', notes=notes, volume_ml=volume, fixed_pairing=fixed_pairing, close_open_loads=True)
        if ok:
            self.accept()
        else:
            QMessageBox.warning(self, t('ui.pen_widget.einfullen_nicht_moglich_00581a84'), msg)
