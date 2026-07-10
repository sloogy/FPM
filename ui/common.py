"""
ui/common.py – Wiederverwendbare UI-Komponenten.

Enthält:
  - EmptyStateWidget  : Einheitlicher Leerzustand mit Icon, Text und CTA-Button
  - ImportPreviewDialog: Validierungsbericht vor CSV-Importen
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton,
    QDialog, QTableWidget, QTableWidgetItem, QDialogButtonBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from ui.ui_scale import scale_px
from i18n.translator import t


class EmptyStateWidget(QWidget):
    """
    Einheitlicher Leerzustand für alle Tabellen und Listen.

    Usage::

        empty = EmptyStateWidget(
            icon="✒",
            title="Noch keine Füller",
            subtitle="Lege deinen ersten Füller an um loszulegen.",
            action_label="+ Füller hinzufügen",
            action_slot=self._add,
        )
        layout.addWidget(empty)
    """
    def __init__(self, icon="📋", title=None,
                 subtitle="", action_label=None, action_slot=None,
                 parent=None):
        super().__init__(parent)
        if title is None:
            title = t("ui.common.no_entries")
        self.setAttribute(
            __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.WidgetAttribute.WA_StyledBackground,
            True
        )
        self.setStyleSheet("background:transparent;")
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)
        layout.setContentsMargins(40, 40, 40, 40)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size:48px; color:#d5dce6; border:none;")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_lbl)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size:16px; font-weight:bold; color:#7f8c8d; border:none;")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_lbl)

        if subtitle:
            sub_lbl = QLabel(subtitle)
            sub_lbl.setWordWrap(True)
            sub_lbl.setStyleSheet("font-size:13px; color:#95a5a6; border:none;")
            sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(sub_lbl)

        if action_label and action_slot:
            btn = QPushButton(action_label)
            btn.setStyleSheet(
                "background:#3498db; color:white; border:none;"
                " padding:8px 20px; border-radius:5px; font-weight:bold;"
                " font-size:13px;"
            )
            btn.clicked.connect(action_slot)
            layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)


class ImportPreviewDialog(QDialog):
    """Zeigt CSV-Import-Vorschau mit Validierungsbericht.

    Nutzer sieht gültige Zeilen, Warnungen und Fehler bevor etwas importiert wird.
    Der Dialog gibt nur ``Accepted`` zurück wenn der Nutzer explizit bestätigt.

    Usage::

        results = [
            {"line": 2, "label": "Pilot Iroshizuku", "status": "ok",   "msg": "OK"},
            {"line": 3, "label": "?",                 "status": "error","msg": "Marke fehlt"},
            {"line": 4, "label": "Pelikan M800",      "status": "warn", "msg": "Datum unklar: '13/2/24'"},
        ]
        dlg = ImportPreviewDialog(results, "Füller-Import Vorschau", parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            # importieren
    """

    STATUS_COLORS = {
        "ok":    ("#27ae60", "✅"),
        "warn":  ("#f39c12", "⚠️"),
        "error": ("#e74c3c", "❌"),
    }

    def __init__(self, results: list, title: str | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title or t("common.import_preview_title"))
        self.setMinimumSize(scale_px(660), scale_px(440))
        root = QVBoxLayout(self)
        root.setSpacing(10)

        ok    = [r for r in results if r["status"] == "ok"]
        warn  = [r for r in results if r["status"] == "warn"]
        error = [r for r in results if r["status"] == "error"]

        summary = QLabel(t(
            'ui.common.import_preview_summary_html',
            total=len(results), ok=len(ok), warn=len(warn), error=len(error),
        ))
        summary.setWordWrap(True)
        root.addWidget(summary)

        table = QTableWidget(len(results), 4)
        table.setHorizontalHeaderLabels([t('ui.common.zeile_fc9f3402'), t('ui.common.eintrag_fb184b4b'), t('ui.common.status_bd7e778c'), t('ui.common.hinweis_06caf4c0')])
        table.horizontalHeader().setStretchLastSection(True)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        for row_idx, r in enumerate(results):
            color_hex, icon = self.STATUS_COLORS.get(r["status"], ("#888", "?"))
            color = QColor(color_hex)

            items = [
                QTableWidgetItem(str(r.get("line", ""))),
                QTableWidgetItem(r.get("label", "")),
                QTableWidgetItem(f"{icon} {r['status'].upper()}"),
                QTableWidgetItem(r.get("msg", "")),
            ]
            for col_idx, item in enumerate(items):
                item.setForeground(color)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                table.setItem(row_idx, col_idx, item)

        table.resizeColumnsToContents()
        root.addWidget(table)

        if error:
            note = QLabel(t('ui.common.import_errors_skipped', count=len(error)))
            note.setStyleSheet("color:#e74c3c; font-size:12px;")
            root.addWidget(note)

        importable = len(ok) + len(warn)
        bb = QDialogButtonBox()
        if importable:
            import_btn = bb.addButton(
                t('ui.common.import_rows', count=importable),
                QDialogButtonBox.ButtonRole.AcceptRole,
            )
            import_btn.setStyleSheet(
                "background:#27ae60;color:white;border:none;"
                "padding:7px 16px;border-radius:5px;font-weight:bold;"
            )
        bb.addButton(t('common.cancel'), QDialogButtonBox.ButtonRole.RejectRole)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        root.addWidget(bb)


class ImageZoomDialog(QDialog):
    """Große Bildansicht (Usability-Befund 3.4, Briefing-Anforderung).

    Zeigt ein Pixmap auf bis zu 85% der Bildschirmgröße skaliert; größere
    Bilder bleiben per Scrollbereich erreichbar.
    """

    def __init__(self, pixmap, title: str = "", parent=None):
        super().__init__(parent)
        from PySide6.QtWidgets import QScrollArea, QApplication
        self.setWindowTitle(title or t("common.image_zoom_title"))
        root = QVBoxLayout(self)
        screen = QApplication.primaryScreen().availableGeometry()
        max_w, max_h = int(screen.width() * 0.85), int(screen.height() * 0.85)
        if pixmap.width() > max_w or pixmap.height() > max_h:
            pixmap = pixmap.scaled(max_w, max_h, Qt.AspectRatioMode.KeepAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)
        label = QLabel()
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setPixmap(pixmap)
        area = QScrollArea()
        area.setWidget(label)
        area.setWidgetResizable(True)
        root.addWidget(area)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(self.reject)
        bb.clicked.connect(self.accept)
        root.addWidget(bb)
        self.resize(min(pixmap.width() + 48, max_w + 48), min(pixmap.height() + 96, max_h + 96))
