"""
Dialog zum Bearbeiten der Rotationsrollen-Regeln.

Pro Rolle konfigurierbar:
- Nässe min/max
- Max. Reinigungsaufwand
- Shimmer / Pigment: Erlaubt / Vermeiden / Neutral
- Sheen / Shading bevorzugen
- Bevorzugte Tinten-Tags (usage_tags)
- Typische Federgrössen und Füllsysteme (informell, keine harte Filterung)
- Score-Bonus bei Übereinstimmung
"""
from __future__ import annotations
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QScrollArea, QWidget,
    QGroupBox, QFormLayout, QLabel, QSpinBox, QComboBox,
    QCheckBox, QPushButton, QMessageBox, QTabWidget,
)
from PySide6.QtCore import Qt

from i18n.translator import t
from logic.role_config import (
    load_role_configs, save_role_configs, reset_role_configs,
    load_theme_configs, save_theme_configs, reset_theme_configs,
    DEFAULT_ROLE_CONFIGS, DEFAULT_THEME_CONFIGS, NIB_SIZE_CATEGORIES,
)


# ── Rollen-Anzeigenamen (sync mit pen_widget ROTATION_ROLES) ─────────────────
def _role_display(code: str) -> str:
    mapping = {
        "writer": t("rotation.role_writer"),   "edc":      t("rotation.role_edc"),
        "agenda": t("rotation.role_agenda"),   "journal":  t("rotation.role_journal"),
        "work":   t("rotation.role_work"),     "creative": t("rotation.role_creative"),
        "letter": t("rotation.role_letter"),   "collector":t("rotation.role_collector"),
        "vintage":t("rotation.role_vintage"),  "problem":  t("rotation.role_problem"),
        "fine":   t("rotation.role_fine"),     "broad":    t("rotation.role_broad"),
        "must":   "Pflicht-Füller",
    }
    return mapping.get(code, code)


def _theme_display(code: str) -> str:
    key = f"rotation.theme_{code}"
    lbl = t(key)
    return code if lbl == key else lbl


_TRISTATE = [(None, t("rotation.role_neutral")),
             (True, t("rotation.role_allow")),
             (False, t("rotation.role_avoid"))]

_ALL_TAGS = [
    ("edc","edc"), ("agenda","agenda"), ("work","work"), ("business","business"),
    ("document","document"), ("archive","archive"), ("journal","journal"),
    ("letter","letter"), ("creative","creative"), ("sheen_showcase","sheen_showcase"),
    ("shading","shading"), ("fine_nib","fine_nib"), ("broad_nib","broad_nib"),
    ("cheap_paper","cheap_paper"), ("easy_clean","easy_clean"),
    ("collector_safe","collector_safe"), ("vintage_safe","vintage_safe"),
    ("testing","testing"), ("waterproof","waterproof"),
]

_FILL_SYSTEMS = [
    ("piston", "Kolbenfüller"), ("vac", "Vac"),
    ("converter", "Converter"), ("cartridge", "Patrone"),
    ("eyedropper", "Eyedropper"),
]


class _RolePanel(QWidget):
    """Ein Tab-Panel pro Rolle."""

    def __init__(self, role_code: str, cfg: dict, parent=None):
        super().__init__(parent)
        self.role_code = role_code
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        inner = QWidget(); fl = QFormLayout(inner); fl.setSpacing(6)

        # ── Nässe ──
        h_wet = QHBoxLayout()
        self.wet_min = QSpinBox(); self.wet_min.setRange(1, 5)
        self.wet_min.setValue(cfg.get("min_wetness") or 1)
        self.wet_max = QSpinBox(); self.wet_max.setRange(1, 5)
        self.wet_max.setValue(cfg.get("max_wetness") or 5)
        h_wet.addWidget(self.wet_min); h_wet.addWidget(QLabel("–")); h_wet.addWidget(self.wet_max)
        fl.addRow(t("rotation.role_col_wetness"), h_wet)

        # ── Reinigung max ──
        self.clean_max = QSpinBox(); self.clean_max.setRange(1, 5)
        self.clean_max.setValue(cfg.get("max_cleaning") or 5)
        fl.addRow(t("rotation.role_col_cleaning"), self.clean_max)

        # ── Shimmer ──
        self.shimmer_combo = QComboBox()
        for val, label in _TRISTATE:
            self.shimmer_combo.addItem(label, val)
        self.shimmer_combo.setCurrentIndex(
            {None: 0, True: 1, False: 2}.get(cfg.get("allow_shimmer"), 0))
        fl.addRow(t("rotation.role_col_shimmer"), self.shimmer_combo)

        # ── Pigment ──
        self.pigment_combo = QComboBox()
        for val, label in _TRISTATE:
            self.pigment_combo.addItem(label, val)
        self.pigment_combo.setCurrentIndex(
            {None: 0, True: 1, False: 2}.get(cfg.get("allow_pigment"), 0))
        fl.addRow(t("rotation.role_col_pigment"), self.pigment_combo)

        # ── Sheen / Shading ──
        self.sheen_cb   = QCheckBox(); self.sheen_cb.setChecked(bool(cfg.get("prefer_sheen")))
        self.shading_cb = QCheckBox(); self.shading_cb.setChecked(bool(cfg.get("prefer_shading")))
        fl.addRow(t("rotation.role_col_sheen"),   self.sheen_cb)
        fl.addRow(t("rotation.role_col_shading"), self.shading_cb)

        # ── Tinten-Tags ──
        tags_grp = QGroupBox(t("rotation.role_col_tags"))
        tags_v = QVBoxLayout(tags_grp); tags_v.setSpacing(2)
        self.tag_cbs: dict[str, QCheckBox] = {}
        current_tags = set(cfg.get("target_tags") or [])
        row_h = None
        for i, (code, _) in enumerate(_ALL_TAGS):
            if i % 4 == 0:
                row_h = QHBoxLayout(); tags_v.addLayout(row_h)
            cb = QCheckBox(code); cb.setChecked(code in current_tags)
            self.tag_cbs[code] = cb
            row_h.addWidget(cb)
        fl.addRow(tags_grp)

        # ── Federgrössen (Checkboxes, fließen in Scoring ein) ──────────
        nib_grp = QGroupBox(t("rotation.role_col_nibs"))
        nib_grp.setToolTip(t("rotation.role_nib_hint"))
        nib_h = QHBoxLayout(nib_grp)
        self.nib_cbs: dict[str, QCheckBox] = {}
        pref_nibs = set(cfg.get("preferred_nib_sizes") or [])
        for code, _label in NIB_SIZE_CATEGORIES:
            cb = QCheckBox(t(f"rotation.role_nib_{code}"))
            cb.setToolTip(t("rotation.role_nib_hint"))
            cb.setChecked(code in pref_nibs)
            self.nib_cbs[code] = cb
            nib_h.addWidget(cb)
        fl.addRow(nib_grp)

        # ── Füllsysteme ──
        fs_grp = QGroupBox(t("rotation.role_col_systems"))
        fs_h = QHBoxLayout(fs_grp)
        self.fs_cbs: dict[str, QCheckBox] = {}
        pref_fs = set(cfg.get("preferred_fill_systems") or [])
        for code, label in _FILL_SYSTEMS:
            cb = QCheckBox(label); cb.setChecked(code in pref_fs)
            self.fs_cbs[code] = cb; fs_h.addWidget(cb)
        fl.addRow(fs_grp)

        # ── Score-Bonus ──
        h_score = QHBoxLayout()
        self.score_match = QSpinBox(); self.score_match.setRange(0, 50)
        self.score_match.setValue(int(cfg.get("score_match") or 12))
        self.score_miss  = QSpinBox(); self.score_miss.setRange(-50, 0)
        self.score_miss.setValue(int(cfg.get("score_miss") or -8))
        h_score.addWidget(QLabel("+")); h_score.addWidget(self.score_match)
        h_score.addWidget(QLabel(" / ")); h_score.addWidget(self.score_miss)
        fl.addRow(t("rotation.role_col_bonus"), h_score)

        inner.setLayout(fl)
        scroll.setWidget(inner)
        layout.addWidget(scroll)

    def get_config(self) -> dict:
        idx_to_val = {0: None, 1: True, 2: False}
        return {
            "min_wetness": self.wet_min.value(),
            "max_wetness": self.wet_max.value(),
            "max_cleaning": self.clean_max.value(),
            "allow_shimmer": idx_to_val[self.shimmer_combo.currentIndex()],
            "allow_pigment": idx_to_val[self.pigment_combo.currentIndex()],
            "prefer_sheen":  self.sheen_cb.isChecked(),
            "prefer_shading":self.shading_cb.isChecked(),
            "target_tags": [code for code, cb in self.tag_cbs.items() if cb.isChecked()],
            "preferred_nib_sizes": [code for code, cb in self.nib_cbs.items() if cb.isChecked()],
            "preferred_fill_systems": [c for c, cb in self.fs_cbs.items() if cb.isChecked()],
            "score_match": self.score_match.value(),
            "score_miss":  self.score_miss.value(),
        }


class RolePrefsDialog(QDialog):
    """Haupt-Dialog: Tabs pro Rolle."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("rotation.role_editor_title"))
        self.resize(700, 580)
        self._configs = load_role_configs()

        root = QVBoxLayout(self)

        hint = QLabel(t("rotation.role_editor_hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#555; font-size:12px; margin-bottom:6px;")
        root.addWidget(hint)

        self._theme_configs = load_theme_configs()

        # Aeussere Tabs: Rollen | Themen
        outer = QTabWidget()

        roles_container = QWidget(); roles_v = QVBoxLayout(roles_container)
        roles_v.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget()
        self._panels: dict[str, _RolePanel] = {}
        for code in DEFAULT_ROLE_CONFIGS:
            cfg = self._configs.get(code, {})
            panel = _RolePanel(code, cfg)
            self._panels[code] = panel
            tab_label = _role_display(code)
            if code == "must":
                tab_label += " *"
            self.tabs.addTab(panel, tab_label)
        roles_v.addWidget(self.tabs)
        outer.addTab(roles_container, t("rotation.editor_tab_roles"))

        themes_container = QWidget(); themes_v = QVBoxLayout(themes_container)
        themes_v.setContentsMargins(0, 0, 0, 0)
        theme_hint = QLabel(t("rotation.theme_editor_hint"))
        theme_hint.setWordWrap(True)
        theme_hint.setStyleSheet("color:#555; font-size:12px; margin-bottom:6px;")
        themes_v.addWidget(theme_hint)
        self.theme_tabs = QTabWidget()
        self._theme_panels: dict[str, _RolePanel] = {}
        for code in DEFAULT_THEME_CONFIGS:
            cfg = self._theme_configs.get(code, {})
            panel = _RolePanel(code, cfg)
            self._theme_panels[code] = panel
            self.theme_tabs.addTab(panel, _theme_display(code))
        themes_v.addWidget(self.theme_tabs)
        outer.addTab(themes_container, t("rotation.editor_tab_themes"))

        root.addWidget(outer)

        # Buttons
        btn_row = QHBoxLayout()
        btn_reset = QPushButton(t("rotation.role_reset"))
        btn_reset.setStyleSheet("background:#e74c3c;color:white;border:none;padding:7px 14px;border-radius:4px;")
        btn_reset.clicked.connect(self._reset)
        btn_row.addWidget(btn_reset)
        btn_row.addStretch()
        btn_cancel = QPushButton(t("common.cancel"))
        btn_cancel.setStyleSheet("background:#7f8c8d;color:white;border:none;padding:7px 14px;border-radius:4px;")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)
        btn_save = QPushButton(t("rotation.role_save"))
        btn_save.setStyleSheet("background:#27ae60;color:white;border:none;padding:7px 14px;border-radius:4px;")
        btn_save.clicked.connect(self._save)
        btn_row.addWidget(btn_save)
        root.addLayout(btn_row)

    def _save(self):
        role_cfgs = {code: panel.get_config() for code, panel in self._panels.items()}
        save_role_configs(role_cfgs)
        theme_cfgs = {code: panel.get_config() for code, panel in self._theme_panels.items()}
        save_theme_configs(theme_cfgs)
        QMessageBox.information(self, t("rotation.role_editor_title"), t("rotation.role_saved_ok"))
        self.accept()

    def _reset(self):
        from PySide6.QtWidgets import QMessageBox
        r = QMessageBox.question(self, t("rotation.role_reset"),
            t("rotation.role_reset_q"))
        if r == QMessageBox.StandardButton.Yes:
            reset_role_configs()
            reset_theme_configs()
            self.reject()
