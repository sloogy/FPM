"""
ui/common.py – Wiederverwendbare UI-Komponenten.

Enthält:
  - EmptyStateWidget  : Einheitlicher Leerzustand mit Icon, Text und CTA-Button
  - ImportPreviewDialog: Validierungsbericht vor CSV-Importen
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton,
    QDialog, QTableWidget, QTableWidgetItem, QDialogButtonBox,
    QScrollArea, QApplication, QFrame, QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor

from i18n.translator import t




class ResponsiveDialog(QDialog):
    """QDialog-Basis mit bildschirmbegrenzter Geometrie und optionalem Scrollinhalt.

    Qt-Geometrien liegen bereits in logischen Pixeln vor. Die Klasse begrenzt
    Mindest-, Maximal- und Startgröße deshalb direkt gegen die verfügbare
    Bildschirmfläche und verhindert, dass Schaltflächen auf Laptop-Displays
    außerhalb des sichtbaren Bereichs liegen.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._responsive_preferred = (720, 560)
        self._responsive_minimum = (360, 280)
        self._responsive_margin = 24
        self._responsive_wrapped = False
        self._responsive_scroll = None
        self._responsive_content = None

    def enable_responsive_layout(
        self,
        preferred_width: int = 720,
        preferred_height: int = 560,
        *,
        minimum_width: int = 360,
        minimum_height: int = 280,
        scroll: bool = True,
        sticky_buttons: bool = True,
        margin: int = 24,
    ) -> None:
        self._responsive_preferred = (max(1, preferred_width), max(1, preferred_height))
        self._responsive_minimum = (max(1, minimum_width), max(1, minimum_height))
        self._responsive_margin = max(8, margin)
        if scroll and not self._responsive_wrapped:
            self._wrap_root_layout(sticky_buttons=sticky_buttons)
        self._fit_to_available_screen()
        QTimer.singleShot(0, self._fit_to_available_screen)

    def _wrap_root_layout(self, *, sticky_buttons: bool) -> None:
        root = self.layout()
        if root is None or self._responsive_wrapped:
            return

        margins = root.contentsMargins()
        spacing = root.spacing()
        content = QWidget(self)
        content.setObjectName("responsiveDialogContent")
        content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(
            margins.left(), margins.top(), margins.right(), margins.bottom()
        )
        content_layout.setSpacing(max(0, spacing))

        sticky = []
        while root.count():
            item = root.takeAt(0)
            widget = item.widget()
            if sticky_buttons and isinstance(widget, QDialogButtonBox):
                sticky.append(widget)
            elif widget is not None:
                content_layout.addWidget(widget)
            elif item.layout() is not None:
                content_layout.addLayout(item.layout())
            else:
                content_layout.addItem(item)

        scroll = QScrollArea(self)
        scroll.setObjectName("responsiveDialogScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setWidget(content)

        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(scroll, 1)
        for button_box in sticky:
            button_box.setContentsMargins(8, 6, 8, 8)
            root.addWidget(button_box, 0)

        self._responsive_wrapped = True
        self._responsive_scroll = scroll
        self._responsive_content = content

    def _available_geometry(self):
        screen = self.screen()
        if screen is None:
            screen = QApplication.screenAt(self.frameGeometry().center())
        if screen is None:
            screen = QApplication.primaryScreen()
        return screen.availableGeometry() if screen is not None else None

    def _fit_to_available_screen(self) -> None:
        available = self._available_geometry()
        pref_w, pref_h = self._responsive_preferred
        min_w, min_h = self._responsive_minimum
        if available is None:
            self.setMinimumSize(min_w, min_h)
            self.resize(pref_w, pref_h)
            return

        max_w = max(320, available.width() - 2 * self._responsive_margin)
        max_h = max(240, available.height() - 2 * self._responsive_margin)
        bounded_min_w = min(min_w, max_w)
        bounded_min_h = min(min_h, max_h)
        target_w = min(max(pref_w, bounded_min_w), max_w)
        target_h = min(max(pref_h, bounded_min_h), max_h)

        self.setMinimumSize(bounded_min_w, bounded_min_h)
        self.setMaximumSize(max_w, max_h)
        self.resize(target_w, target_h)

    def showEvent(self, event) -> None:
        self._fit_to_available_screen()
        super().showEvent(event)


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
        title_lbl.setStyleSheet("font-size:16px; font-weight:bold; color:#5f6f72; border:none;")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_lbl)

        if subtitle:
            sub_lbl = QLabel(subtitle)
            sub_lbl.setWordWrap(True)
            sub_lbl.setStyleSheet("font-size:13px; color:#5f6f72; border:none;")
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


class ImportPreviewDialog(ResponsiveDialog):
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
        self.enable_responsive_layout(760, 560, minimum_width=420, minimum_height=320)


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


def open_in_file_manager(parent, folder) -> bool:
    """Öffnet einen Ordner im Dateimanager des Systems. True bei Erfolg.

    Lag bis Loop 32 nur in ``ui/settings_widget.py``. Seit die Menüleiste
    denselben Befehl anbietet, gibt es zwei Aufrufer - und damit den üblichen
    Grund, warum eine Kopie irgendwann abweicht.
    """
    import subprocess
    import sys
    from pathlib import Path

    from PySide6.QtWidgets import QMessageBox

    ordner = Path(folder)
    try:
        if sys.platform.startswith('linux'):
            subprocess.Popen(['xdg-open', str(ordner)])
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', str(ordner)])
        else:
            import os
            os.startfile(str(ordner))  # type: ignore[attr-defined]
        return True
    except OSError as fehler:
        QMessageBox.warning(
            parent,
            t('settings.folder_open_title'),
            t('settings.folder_open_err', error=fehler),
        )
        return False
