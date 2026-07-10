"""Einfache Calibre-artige Navigation mit DAU-freundlichen Gruppen."""
from __future__ import annotations

from typing import Dict
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QDialog

from app_info import APP_NAME, APP_VERSION
from ui.ui_scale import scale_px
from i18n.translator import t
from logic.app_mode import EXPERT_MODE, SIMPLE_MODE, fallback_page, get_app_mode, set_app_mode

MODULES: Dict[str, dict] = {
    "dashboard": {"title_key": "nav.dashboard", "icon": "🏠", "page": 0},
    "pens": {"title_key": "nav.pens", "icon": "✒", "page": 1},
    "inks": {"title_key": "nav.inks", "icon": "🖋", "page": 2},
    "nibs": {"title_key": "nav.nibs", "icon": "🔧", "page": 3},
    "paper": {"title_key": "nav.paper", "icon": "📋", "page": 4},
    "samples": {"title_key": "nav.samples", "icon": "📝", "page": 12},
    "enthusiast_lab": {"title_key": "nav.enthusiast_lab", "icon": "🧪", "page": 13},
    "rotation": {"title_key": "nav.rotation", "icon": "🔄", "page": 5},
    "expenses": {"title_key": "nav.expenses", "icon": "💰", "page": 6},
    "statistics": {"title_key": "nav.statistics", "icon": "📊", "page": 11},
    "wishlist": {"title_key": "nav.wishlist", "icon": "🧾", "page": 7},
    "rules": {"title_key": "nav.rules", "icon": "⚙", "page": 8},
    "help": {"title_key": "nav.help", "icon": "❔", "page": 9},
    "settings": {"title_key": "nav.settings", "icon": "☰", "page": 10},
}

# DAU-Logik: nicht eine lange Werkzeugkastenliste, sondern ein Arbeitsfluss.
# Simple Mode zeigt nur die Start-/Alltagsmodule plus Hilfe/Einstellungen.
GROUPED_ORDER_SIMPLE = [
    ("nav.group_start", ["dashboard"]),
    ("nav.group_quickstart", ["pens", "inks", "rotation"]),
    ("nav.group_system", ["help", "settings"]),
]

# Expert Mode zeigt die komplette Sammler-/Analyse-/Regel-Werkbank.
GROUPED_ORDER_EXPERT = [
    ("nav.group_start", ["dashboard"]),
    ("nav.group_collection", ["pens", "inks", "nibs", "paper"]),
    ("nav.group_usage", ["rotation", "samples", "wishlist", "expenses"]),
    ("nav.group_analysis", ["statistics", "enthusiast_lab"]),
    ("nav.group_system", ["rules", "help", "settings"]),
]

# Rückwärtskompatibilität für Tests/alte Imports.
GROUPED_ORDER = GROUPED_ORDER_EXPERT
ORDER = [mid for _group, mids in GROUPED_ORDER_EXPERT for mid in mids]
PAGE_SHORTCUTS = {
    0: "Ctrl+1",
    1: "Ctrl+2",
    2: "Ctrl+3",
    3: "Ctrl+4",
    4: "Ctrl+5",
    5: "Ctrl+6",
    6: "Ctrl+7",
    7: "Ctrl+8",
    8: "Ctrl+9",
    9: "Alt+1",
    10: "Alt+2",
    11: "Alt+3",
    12: "Alt+4",
    13: "Alt+5",
}


class CalibreSidebar(QWidget):
    """Schlichte Seitenleiste: ein Klick = ein Modul, aber klar gruppiert."""

    pageSelected = Signal(int)
    modeChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("simpleSidebar")
        self.setFixedWidth(scale_px(250))
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._buttons: dict[int, QPushButton] = {}
        self._mode = get_app_mode()
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(2)
        self._setup_ui()
        self.set_current_page(0)

    def _clear_layout(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _setup_ui(self):
        self._clear_layout()
        self._buttons.clear()
        self._mode = get_app_mode()
        layout = self._layout

        logo = QLabel(f"✒  {APP_NAME}")
        logo.setObjectName("sidebarLogo")
        layout.addWidget(logo)

        grouped_order = GROUPED_ORDER_EXPERT if self._mode == EXPERT_MODE else GROUPED_ORDER_SIMPLE
        for group_key, module_ids in grouped_order:
            group_label = QLabel(t(group_key).upper())
            group_label.setObjectName("sidebarGroupLabel")
            layout.addWidget(group_label)
            for mid in module_ids:
                meta = MODULES[mid]
                page = int(meta["page"])
                shortcut = PAGE_SHORTCUTS.get(page, "")
                suffix = f"  {shortcut}" if shortcut else ""
                btn = QPushButton(f"{meta['icon']}  {t(meta['title_key'])}{suffix}")
                btn.setObjectName("navButton")
                btn.setToolTip(t("ui.navigation.module_shortcut", module=t(meta["title_key"]), shortcut=shortcut or "—"))
                btn.setCheckable(True)
                btn.clicked.connect(lambda checked=False, p=page: self._select(p))
                layout.addWidget(btn)
                self._buttons[page] = btn

        layout.addStretch(1)
        mode_btn_text = t(
            "ui.navigation.switch_to_simple" if self._mode == EXPERT_MODE else "ui.navigation.switch_to_expert"
        )
        mode_btn = QPushButton(mode_btn_text)
        mode_btn.setObjectName("modeToggleButton")
        mode_btn.setToolTip(t("ui.navigation.mode_toggle_tooltip"))
        mode_btn.clicked.connect(self._toggle_mode)
        layout.addWidget(mode_btn)
        hint_key = "ui.navigation.expert_mode_hint" if self._mode == EXPERT_MODE else "ui.navigation.simple_mode_hint"
        hint = QLabel(t(hint_key))
        hint.setObjectName("sidebarHint")
        layout.addWidget(hint)
        version = QLabel(APP_VERSION)
        version.setObjectName("sidebarVersion")
        layout.addWidget(version)

    def _select(self, page: int):
        page = fallback_page(page, self._mode)
        self.set_current_page(page)
        self.pageSelected.emit(page)

    def set_mode(self, mode: str) -> str:
        """Modus programmatisch setzen und Navigation neu aufbauen."""
        self._mode = set_app_mode(mode)
        self._setup_ui()
        return self._mode

    def _toggle_mode(self) -> None:
        new_mode = EXPERT_MODE if self._mode == SIMPLE_MODE else SIMPLE_MODE
        self.set_mode(new_mode)
        self.modeChanged.emit(self._mode)

    def set_current_page(self, page: int):
        for p, btn in self._buttons.items():
            btn.setChecked(p == page)


# Rückwärtskompatibler Name für bestehende Imports
ObsidianSidebar = CalibreSidebar


class NavigationSettingsDialog(QDialog):
    """Kompatibilitätsdialog: In der Calibre-Ansicht ist die Navigation bewusst fest."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t('ui.navigation.navigation_0871a7fb'))
        self.setModal(True)
        self.resize(scale_px(420), scale_px(180))
        layout = QVBoxLayout(self)
        text = QLabel(
            t('ui.navigation.navigation_mode_dialog_body')
        )
        text.setWordWrap(True)
        layout.addWidget(text)
        ok = QPushButton(t('ui.navigation.ok_d0686962'))
        ok.clicked.connect(self.accept)
        layout.addWidget(ok)
