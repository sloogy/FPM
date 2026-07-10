"""Regelverwaltung, Reinigungszeiten und Full-Auto-Konfiguration.

v0.2.32:
- Regeln-Seite in lesbare Reiter zerlegt.
- Jede Reiterseite hat bei Bedarf eigenen Scrollbereich.
- Laptop-/Lesbarkeits-Skalierung direkt in der Regeln-Seite.
- Verbrauch/Restmenge ist in Easy Mode bewusst gesperrt, aber mit einem klaren
  Expert-Mode-Schalter aktivierbar.
- Regelgruppen-Speichern schreibt den Bedienmodus mit, damit Verbrauch nach dem
  Umschalten auf Expert wirklich aktiv werden kann.
"""
from __future__ import annotations

import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QCheckBox,
    QHeaderView,
)

from ui.ui_scale import scale_px
from database.db import get_session
from database.models import AppSettings, Rule
from logic.auto_mode_service import RULE_GROUPS
from i18n.translator import t

CONDITION_KEYS = [
    "fill_system_ink_prop",
    "nib_size_wetness",
    "ink_prop_warning",
    "pen_tag_ink_prop",
    "pen_tag_sheen_cleaning",
    "nib_grind_prefers_ink_prop",
]

def _condition_label(key: str | None) -> str:
    return t(f"rules.conditions.{key}") if key else ""

def _rule_group_label(key: str | None) -> str:
    return t(f"rules.groups.{key}") if key else ""


_LEVEL_ICONS = {"info": "🔵", "warning": "🟠", "critical": "🔴", "blocked": "⛔"}


def _warn_level_label(level: str | None) -> str:
    """Warnstufe mit Icon + Übersetzung statt rohem Code (v0.2.79)."""
    key = (level or "").strip().lower()
    if key in ("info", "warning", "critical", "blocked"):
        return f"{_LEVEL_ICONS[key]} {t('rules.' + key)}"
    return level or ""


def _rule_type_label(rule_type: str | None) -> str:
    """Regeltyp übersetzt statt rohem 'hard'/'soft' (v0.2.79)."""
    key = (rule_type or "").strip().lower()
    if key == "hard":
        return t("rules.type_hard")
    if key == "soft":
        return t("rules.type_soft")
    return rule_type or ""

GROUP_ORDER = [
    "safety",
    "ink_fill",
    "consumption",
    "maintenance",
    "rotation",
    "pen",
    "ink",
    "nib",
    "paper",
    "collector",
]

_TRUTHY = {"1", "true", "yes", "ja", "on"}


def _is_true(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in _TRUTHY


class RulesWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("rulesWidget")
        self._all_rules: list[Rule] = []
        self._setup_ui()
        self.refresh()

    # ------------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------------
    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        hdr = QHBoxLayout()
        title = QLabel(t('ui.rules_widget.regeln_reinigungszeiten_da58b474'))
        title.setObjectName("page_title")
        hdr.addWidget(title)
        hdr.addStretch()

        scale_label = QLabel(t('ui.rules_widget.ansicht_f3b72c1e'))
        self.scale_combo = QComboBox()
        self.scale_combo.setMinimumWidth(scale_px(140))
        self.scale_combo.addItem(t('ui.rules_widget.kompakt_bf49a75c'), "0.90")
        self.scale_combo.addItem(t('ui.rules_widget.normal_abe7e201'), "1.00")
        self.scale_combo.addItem(t('ui.rules_widget.laptop_gro_0f4dbd5b'), "1.15")
        self.scale_combo.addItem(t('ui.rules_widget.sehr_gro_3062ff78'), "1.30")
        self.scale_combo.currentIndexChanged.connect(self._save_and_apply_scale)
        hdr.addWidget(scale_label)
        hdr.addWidget(self.scale_combo)

        add = QPushButton(t('ui.rules_widget.regel_81add3ac'))
        add.setObjectName("primaryAction")
        add.clicked.connect(self._add)
        hdr.addWidget(add)
        root.addLayout(hdr)

        # v0.2.80: Kurzlogik ganz oben (B-Position) – sichtbar auf jedem Tab.
        # Ersetzt den früheren Reiter-Hinweis (durch die Tabs selbst redundant).
        overview = QLabel(t('rules.overview_explain'))
        overview.setObjectName("rulesOverview")
        overview.setWordWrap(True)
        overview.setStyleSheet(
            "background:#f8fafc; border:1px solid #dbe4ef; border-radius:8px;"
            "padding:10px 12px; color:#334155; font-size:13px;"
        )
        root.addWidget(overview)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        root.addWidget(self.tabs, 1)

        self._build_cleaning_tab()
        self._build_auto_tab()
        self._build_groups_tab()
        self._build_rules_tab()

    def _scroll_page(self) -> tuple[QWidget, QVBoxLayout]:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        scroll.setWidget(body)
        return scroll, layout

    def _build_cleaning_tab(self):
        page, layout = self._scroll_page()
        grp = QGroupBox(t('ui.rules_widget.standardzeiten_bis_zur_reinigung_504c0286'))
        fl = QFormLayout(grp)
        fl.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        fl.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        fl.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.normal = QSpinBox(); self.normal.setRange(1, 180); self.normal.setSuffix(t('ui.rules_widget.tage_f7fc9883'))
        self.shimmer = QSpinBox(); self.shimmer.setRange(1, 180); self.shimmer.setSuffix(t('ui.rules_widget.tage_f7fc9883'))
        self.pigment = QSpinBox(); self.pigment.setRange(1, 180); self.pigment.setSuffix(t('ui.rules_widget.tage_f7fc9883'))
        self.grail = QSpinBox(); self.grail.setRange(1, 180); self.grail.setSuffix(t('ui.rules_widget.tage_f7fc9883'))
        for label, widget in [
            (t("ui.rules_widget.normal_ink"), self.normal),
            ("Shimmer", self.shimmer),
            ("Pigment/Wasserfest", self.pigment),
            ("Grail Pen", self.grail),
        ]:
            fl.addRow(label + ":", widget)

        save = QPushButton(t('ui.rules_widget.zeiten_speichern_d8ed63fe'))
        save.clicked.connect(self._save_settings)
        fl.addRow("", save)
        layout.addWidget(grp)
        layout.addStretch(1)
        self.tabs.addTab(page, t('ui.rules_widget.zeiten_9cccc725'))

    def _build_auto_tab(self):
        page, layout = self._scroll_page()
        auto_grp = QGroupBox(t('ui.rules_widget.expertensystem_full_auto_mode_b0c00a52'))
        auto_fl = QFormLayout(auto_grp)
        auto_fl.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.mode_combo = QComboBox()
        self.mode_combo.addItem(t('ui.rules_widget.easy_mode_verbrauch_automatisch_aus_d022a994'), "easy")
        self.mode_combo.addItem(t('ui.rules_widget.expert_mode_verbrauch_kann_aktiviert_werden_b1d65c08'), "expert")
        self.mode_combo.currentIndexChanged.connect(self._sync_mode_ui)
        auto_fl.addRow(t('ui.rules_widget.bedienmodus_ba88ea37'), self.mode_combo)

        self.rules_enabled_cb = QCheckBox(t('ui.rules_widget.regelsystem_aktiv_16585888'))
        self.full_auto_cb = QCheckBox(t('ui.rules_widget.full_auto_mode_aktiv_engine_darf_entscheiden_445e5e5f'))
        self.auto_reject_cb = QCheckBox(t('ui.rules_widget.full_auto_darf_riskante_kombinationen_ablehnen_cba5d537'))
        self.auto_override_cb = QCheckBox(t('ui.rules_widget.full_auto_darf_selbst_override_verwenden_7b17ca93'))
        self.auto_log_cb = QCheckBox(t('ui.rules_widget.auto_entscheidungen_immer_loggen_f14a97e4'))
        for widget in (
            self.rules_enabled_cb,
            self.full_auto_cb,
            self.auto_reject_cb,
            self.auto_override_cb,
            self.auto_log_cb,
        ):
            auto_fl.addRow("", widget)

        note = QLabel(
            t('ui.rules_widget.full_auto_erklart_jede_entscheidung_regel_grund__070d6a1c')
        )
        note.setObjectName("infoText")
        note.setWordWrap(True)
        auto_fl.addRow(t('ui.rules_widget.hinweis_86523c4e'), note)

        save_auto = QPushButton(t('ui.rules_widget.regel_auto_mode_speichern_897f763b'))
        save_auto.clicked.connect(self._save_auto_settings)
        auto_fl.addRow("", save_auto)
        layout.addWidget(auto_grp)
        layout.addStretch(1)
        self.tabs.addTab(page, t('ui.rules_widget.auto_mode_7649ee85'))

    def _build_groups_tab(self):
        page, layout = self._scroll_page()
        group_grp = QGroupBox(t('ui.rules_widget.regelgruppen_einzeln_schalten_ff89458e'))
        group_layout = QVBoxLayout(group_grp)
        group_layout.setSpacing(10)

        self.consumption_status = QLabel()
        self.consumption_status.setObjectName("modeStatus")
        self.consumption_status.setWordWrap(True)
        group_layout.addWidget(self.consumption_status)

        self.enable_consumption_btn = QPushButton(t('ui.rules_widget.expert_mode_aktivieren_verbrauch_einschalten_56e10b52'))
        self.enable_consumption_btn.clicked.connect(self._enable_consumption_tracking)
        group_layout.addWidget(self.enable_consumption_btn)

        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(8)
        self.group_checks: dict[str, QCheckBox] = {}
        for idx, key in enumerate(GROUP_ORDER):
            label = _rule_group_label(key)
            cb = QCheckBox(label)
            cb.setToolTip(
                t('ui.rules_widget.schaltet_diese_regelgruppe_komplett_ein_aus_verb_2fdfbb5a')
            )
            self.group_checks[key] = cb
            row = idx // 2
            col = idx % 2
            grid.addWidget(cb, row, col)
        group_layout.addLayout(grid)

        save_groups = QPushButton(t('ui.rules_widget.regelgruppen_speichern_4aa63cac'))
        save_groups.clicked.connect(self._save_group_settings)
        group_layout.addWidget(save_groups)
        layout.addWidget(group_grp)
        layout.addStretch(1)
        self.tabs.addTab(page, t('ui.rules_widget.regelgruppen_383bf539'))

    def _build_rules_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        filters = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(t('ui.rules_widget.regeln_suchen_9c24f9a0'))
        self.search_edit.textChanged.connect(self._populate_table)
        filters.addWidget(self.search_edit, 1)

        self.group_filter = QComboBox()
        self.group_filter.addItem(t('ui.rules_widget.alle_gruppen_f63501c0'), "")
        for key in GROUP_ORDER:
            self.group_filter.addItem(_rule_group_label(key), key)
        self.group_filter.currentIndexChanged.connect(self._populate_table)
        filters.addWidget(self.group_filter)

        # v0.2.79: zusätzlich nach Warnstufe filtern
        self.level_filter = QComboBox()
        self.level_filter.addItem(t('rules.level_filter_all'), "")
        for level in ("info", "warning", "critical", "blocked"):
            self.level_filter.addItem(_warn_level_label(level), level)
        self.level_filter.currentIndexChanged.connect(self._populate_table)
        filters.addWidget(self.level_filter)
        layout.addLayout(filters)

        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels([
            t('ui.rules_widget.aktiv_2b6ec292'),
            t('ui.rules_widget.wirksam_c2d26d33'),
            t('ui.rules_widget.name_ae656f22'),
            t('ui.rules_widget.gruppe_b13e0a2f'),
            t('ui.rules_widget.typ_e9038577'),
            t('ui.rules_widget.warnstufe_adff5b36'),
            t('ui.rules_widget.auto_577fc765'),
            t('ui.rules_widget.bedingung_3487271b'),
            t('ui.rules_widget.beschreibung_ce56ee78'),
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self._toggle)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._menu)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        layout.addWidget(self.table, 1)

        help_text = QLabel(
            t('ui.rules_widget.doppelklick_auf_eine_regel_schaltet_sie_aktiv_in_f246d9dd')
        )
        help_text.setObjectName("infoText")
        help_text.setWordWrap(True)
        layout.addWidget(help_text)
        self.tabs.addTab(page, t('ui.rules_widget.regelliste_386b6705'))

    # ------------------------------------------------------------------
    # Daten laden / anzeigen
    # ------------------------------------------------------------------
    def refresh(self):
        session = get_session()
        try:
            self.normal.setValue(int(AppSettings.get(session, "cleaning_days_normal", "28")))
            self.shimmer.setValue(int(AppSettings.get(session, "cleaning_days_shimmer", "14")))
            self.pigment.setValue(int(AppSettings.get(session, "cleaning_days_pigment", "10")))
            self.grail.setValue(int(AppSettings.get(session, "cleaning_days_grail", "21")))

            scale = AppSettings.get(session, "rules_ui_scale", "1.15") or "1.15"
            scale_ix = self.scale_combo.findData(scale)
            self.scale_combo.blockSignals(True)
            self.scale_combo.setCurrentIndex(scale_ix if scale_ix >= 0 else self.scale_combo.findData("1.15"))
            self.scale_combo.blockSignals(False)
            self._apply_scale(float(self.scale_combo.currentData() or 1.15))

            mode = AppSettings.get(session, "ui_mode", "easy") or "easy"
            ix = self.mode_combo.findData(mode)
            self.mode_combo.blockSignals(True)
            self.mode_combo.setCurrentIndex(ix if ix >= 0 else 0)
            self.mode_combo.blockSignals(False)

            self.rules_enabled_cb.setChecked(_is_true(AppSettings.get(session, "rules_enabled", "1"), True))
            self.full_auto_cb.setChecked(_is_true(AppSettings.get(session, "full_auto_mode", "0"), False))
            self.auto_reject_cb.setChecked(_is_true(AppSettings.get(session, "full_auto_can_reject", "1"), True))
            self.auto_override_cb.setChecked(_is_true(AppSettings.get(session, "full_auto_can_override", "0"), False))
            self.auto_log_cb.setChecked(_is_true(AppSettings.get(session, "full_auto_logging", "1"), True))

            for key, cb in self.group_checks.items():
                default = "0" if key == "consumption" else "1"
                cb.setChecked(_is_true(AppSettings.get(session, f"rule_group_{key}_enabled", default), default == "1"))

            self._all_rules = session.query(Rule).order_by(Rule.is_system.desc(), Rule.name).all()
            self._sync_mode_ui()
            self._populate_table()
        finally:
            session.close()

    def _group_enabled_cache(self) -> dict[str, bool]:
        return {key: cb.isChecked() and cb.isEnabled() for key, cb in self.group_checks.items()}

    def _populate_table(self):
        if not hasattr(self, "table"):
            return
        query = (self.search_edit.text() if hasattr(self, "search_edit") else "").strip().lower()
        group = self.group_filter.currentData() if hasattr(self, "group_filter") else ""
        level = self.level_filter.currentData() if hasattr(self, "level_filter") else ""
        group_states = self._group_enabled_cache()

        rows = []
        for rule in self._all_rules:
            rule_group = getattr(rule, "rule_group", "") or "rotation"
            text = " ".join([
                rule.name or "",
                rule.description or "",
                rule_group,
                rule.rule_type or "",
                rule.warn_level or "",
                rule.condition_type or "",
            ]).lower()
            if group and rule_group != group:
                continue
            if level and (rule.warn_level or "") != level:
                continue
            if query and query not in text:
                continue
            rows.append(rule)

        self.table.setRowCount(len(rows))
        for row, rule in enumerate(rows):
            rule_group = getattr(rule, "rule_group", "") or "rotation"
            effective = bool(rule.is_active and group_states.get(rule_group, True))
            active_text = "✓" if rule.is_active else "—"
            # v0.2.79: vorher hartes Deutsch in der Wirksam-Spalte –
            # jetzt echte i18n-Keys, damit EN/FR nicht Deutsch zeigen.
            effective_text = t("rules.effective_yes") if effective else t("rules.effective_no")
            if rule.is_active and not group_states.get(rule_group, True):
                effective_text = t("rules.effective_no_group_off")

            active_item = QTableWidgetItem(active_text)
            active_item.setData(Qt.ItemDataRole.UserRole, rule.id)
            self.table.setItem(row, 0, active_item)
            self.table.setItem(row, 1, QTableWidgetItem(effective_text))
            self.table.setItem(row, 2, QTableWidgetItem(rule.name or ""))
            self.table.setItem(row, 3, QTableWidgetItem(_rule_group_label(rule_group) or rule_group))
            self.table.setItem(row, 4, QTableWidgetItem(_rule_type_label(rule.rule_type)))
            self.table.setItem(row, 5, QTableWidgetItem(_warn_level_label(rule.warn_level)))
            self.table.setItem(row, 6, QTableWidgetItem(getattr(rule, "auto_action", "") or "warn"))
            self.table.setItem(row, 7, QTableWidgetItem(_condition_label(rule.condition_type) or (rule.condition_type or "")))
            self.table.setItem(row, 8, QTableWidgetItem(rule.description or ""))

        self._apply_table_geometry()

    def _apply_table_geometry(self):
        scale = float(self.scale_combo.currentData() or 1.15) if hasattr(self, "scale_combo") else 1.15
        if not hasattr(self, "table"):
            return
        widths = [70, 130, 230, 150, 95, 110, 95, 210, 420]
        for col, width in enumerate(widths):
            self.table.setColumnWidth(col, int(width * scale))
        self.table.verticalHeader().setDefaultSectionSize(int(32 * scale))
        self.table.horizontalHeader().setMinimumHeight(int(34 * scale))

    def _sync_mode_ui(self):
        """Easy Mode erzwingt: Verbrauch/Restmenge bleibt aus und ist nicht editierbar."""
        mode = self.mode_combo.currentData() if hasattr(self, "mode_combo") else "easy"
        cb = getattr(self, "group_checks", {}).get("consumption")
        if cb is None:
            return

        if mode == "easy":
            cb.blockSignals(True)
            cb.setChecked(False)
            cb.blockSignals(False)
            cb.setEnabled(False)
            cb.setToolTip(t('ui.rules_widget.im_easy_mode_ist_automatische_verbrauchs_restmen_667375de'))
            self.consumption_status.setText(
                t('ui.rules_widget.verbrauch_restmenge_aus_weil_easy_mode_aktiv_ist_fbe33d0a')
            )
            self.consumption_status.setProperty("state", "off")
            self.enable_consumption_btn.setVisible(True)
        else:
            cb.setEnabled(True)
            cb.setToolTip(t('ui.rules_widget.expert_mode_automatische_restmengen_verbrauchsbu_9da273f6'))
            self.consumption_status.setText(
                t('ui.rules_widget.verbrauch_restmenge_im_expert_mode_frei_schaltba_258b9c51')
            )
            self.consumption_status.setProperty("state", "on")
            self.enable_consumption_btn.setVisible(not cb.isChecked())

        self.consumption_status.style().unpolish(self.consumption_status)
        self.consumption_status.style().polish(self.consumption_status)
        self._populate_table()

    # ------------------------------------------------------------------
    # Skalierung
    # ------------------------------------------------------------------
    def _save_and_apply_scale(self):
        scale = float(self.scale_combo.currentData() or 1.15)
        self._apply_scale(scale)
        session = get_session()
        try:
            AppSettings.set(session, "rules_ui_scale", f"{scale:.2f}")
        finally:
            session.close()

    def _apply_scale(self, scale: float):
        base = max(12, int(14 * scale))
        small = max(11, int(12 * scale))
        title = max(18, int(22 * scale))
        pad_y = max(5, int(7 * scale))
        pad_x = max(8, int(12 * scale))
        self.setStyleSheet(f"""
            QWidget#rulesWidget QLabel,
            QWidget#rulesWidget QCheckBox,
            QWidget#rulesWidget QPushButton,
            QWidget#rulesWidget QComboBox,
            QWidget#rulesWidget QSpinBox,
            QWidget#rulesWidget QLineEdit {{
                font-size: {base}px;
            }}
            QWidget#rulesWidget QLabel#page_title {{
                font-size: {title}px;
                font-weight: 800;
                color: #1e2a38;
            }}
            QWidget#rulesWidget QLabel#rulesHint,
            QWidget#rulesWidget QLabel#infoText {{
                color: #64748b;
                font-size: {small}px;
            }}
            QWidget#rulesWidget QLabel#modeStatus {{
                padding: {pad_y}px {pad_x}px;
                border-radius: 8px;
                background: #eef6ff;
                color: #1e3a8a;
                font-weight: 700;
            }}
            QWidget#rulesWidget QGroupBox {{
                font-size: {base}px;
                font-weight: 700;
                padding: {int(16 * scale)}px {int(12 * scale)}px {int(12 * scale)}px {int(12 * scale)}px;
                margin-top: {int(12 * scale)}px;
            }}
            QWidget#rulesWidget QTabBar::tab {{
                font-size: {base}px;
                padding: {pad_y + 2}px {pad_x + 8}px;
                min-width: {int(95 * scale)}px;
            }}
            QWidget#rulesWidget QPushButton {{
                padding: {pad_y}px {pad_x}px;
                min-height: {int(28 * scale)}px;
            }}
            QWidget#rulesWidget QPushButton#primaryAction {{
                background:#3498db;
                color:white;
                border:none;
                border-radius:6px;
                font-weight:700;
            }}
            QWidget#rulesWidget QTableWidget {{
                font-size: {max(12, int(13 * scale))}px;
            }}
            QWidget#rulesWidget QHeaderView::section {{
                font-size: {max(12, int(13 * scale))}px;
                padding: {pad_y}px {pad_x}px;
            }}
        """)
        self._apply_table_geometry()

    # ------------------------------------------------------------------
    # Speichern
    # ------------------------------------------------------------------
    def _save_settings(self):
        session = get_session()
        try:
            AppSettings.set(session, "cleaning_days_normal", str(self.normal.value()))
            AppSettings.set(session, "cleaning_days_shimmer", str(self.shimmer.value()))
            AppSettings.set(session, "cleaning_days_pigment", str(self.pigment.value()))
            AppSettings.set(session, "cleaning_days_grail", str(self.grail.value()))
            QMessageBox.information(self, t('ui.rules_widget.gespeichert_fc862b34'), t('ui.rules_widget.reinigungszeiten_gespeichert_6b06c57e'))
        finally:
            session.close()

    def _save_auto_settings(self):
        session = get_session()
        try:
            mode = self.mode_combo.currentData() or "easy"
            AppSettings.set(session, "ui_mode", mode)
            AppSettings.set(session, "rules_enabled", "1" if self.rules_enabled_cb.isChecked() else "0")
            AppSettings.set(session, "full_auto_mode", "1" if self.full_auto_cb.isChecked() else "0")
            AppSettings.set(session, "full_auto_can_reject", "1" if self.auto_reject_cb.isChecked() else "0")
            AppSettings.set(session, "full_auto_can_override", "1" if self.auto_override_cb.isChecked() else "0")
            AppSettings.set(session, "full_auto_logging", "1" if self.auto_log_cb.isChecked() else "0")
            if mode == "easy":
                AppSettings.set(session, "rule_group_consumption_enabled", "0")
                self.group_checks["consumption"].setChecked(False)
            self._sync_mode_ui()
            QMessageBox.information(self, t('ui.rules_widget.gespeichert_fc862b34'), t('ui.rules_widget.regelsystem_und_full_auto_mode_gespeichert_673775f0'))
        finally:
            session.close()

    def _save_group_settings(self):
        session = get_session()
        try:
            mode = self.mode_combo.currentData() or AppSettings.get(session, "ui_mode", "easy") or "easy"
            AppSettings.set(session, "ui_mode", mode)
            for key, cb in self.group_checks.items():
                value = "1" if cb.isChecked() else "0"
                if mode == "easy" and key == "consumption":
                    value = "0"
                AppSettings.set(session, f"rule_group_{key}_enabled", value)
            self._sync_mode_ui()
            QMessageBox.information(
                self,
                t('ui.rules_widget.gespeichert_fc862b34'),
                t('ui.rules_widget.regelgruppen_gespeichert_anderungen_wirken_sofor_6667fac8'),
            )
        finally:
            session.close()

    def _enable_consumption_tracking(self):
        """Ein-Klick-Pfad für den häufigen UX-Fall: Verbrauch aktivieren."""
        self.mode_combo.setCurrentIndex(max(0, self.mode_combo.findData("expert")))
        if "consumption" in self.group_checks:
            self.group_checks["consumption"].setEnabled(True)
            self.group_checks["consumption"].setChecked(True)
        self._save_group_settings()

    # ------------------------------------------------------------------
    # Regelaktionen
    # ------------------------------------------------------------------
    def _selected_id(self):
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _menu(self, pos):
        row = self.table.rowAt(pos.y())
        if row >= 0:
            self.table.selectRow(row)
        menu = QMenu(self)
        add = menu.addAction(t('ui.rules_widget.regel_81add3ac'))
        edit = menu.addAction(t('ui.rules_widget.bearbeiten_37991b62'))
        toggle = menu.addAction(t('ui.rules_widget.aktiv_inaktiv_umschalten_4b8aa7d2'))
        delete = menu.addAction(t('ui.rules_widget.loschen_78f9fbc1'))
        has = self._selected_id() is not None
        for action in (edit, toggle, delete):
            action.setEnabled(has)
        act = menu.exec(self.table.viewport().mapToGlobal(pos))
        if act == add:
            self._add()
        elif act == edit:
            self._edit()
        elif act == toggle:
            self._toggle()
        elif act == delete:
            self._delete()

    def _add(self):
        dlg = RuleDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            session = get_session()
            try:
                session.add(Rule(**dlg.data()))
                session.commit()
                self.refresh()
            finally:
                session.close()

    def _edit(self):
        rid = self._selected_id()
        if not rid:
            return
        session = get_session()
        try:
            rule = session.get(Rule, rid)
            if not rule:
                return
            dlg = RuleDialog(self, rule)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                for key, value in dlg.data().items():
                    setattr(rule, key, value)
                session.commit()
                self.refresh()
        finally:
            session.close()

    def _toggle(self):
        rid = self._selected_id()
        if not rid:
            return
        session = get_session()
        try:
            rule = session.get(Rule, rid)
            if rule:
                rule.is_active = not rule.is_active
                session.commit()
                self.refresh()
        finally:
            session.close()

    def _delete(self):
        rid = self._selected_id()
        if not rid:
            return
        session = get_session()
        try:
            rule = session.get(Rule, rid)
            if not rule:
                return
            if getattr(rule, "is_system", False):
                if QMessageBox.question(
                    self,
                    t('ui.rules_widget.systemregel_deaktivieren_c2ce892d'),
                    t('ui.rules_widget.confirm_disable_system_rule', rule=rule.name),
                ) == QMessageBox.StandardButton.Yes:
                    rule.is_active = False
                    session.commit()
                    self.refresh()
                return
            if QMessageBox.question(self, t('ui.rules_widget.loschen_ceb8d0d6'), t('ui.rules_widget.confirm_delete_rule', rule=rule.name)) == QMessageBox.StandardButton.Yes:
                session.delete(rule)
                session.commit()
                self.refresh()
        finally:
            session.close()


class RuleDialog(QDialog):
    def __init__(self, parent=None, rule=None):
        super().__init__(parent)
        self.rule = rule
        self.setWindowTitle(t("rules.edit_title") if rule else t("rules.add_title"))
        self.resize(scale_px(720), scale_px(620))
        self._setup()
        if rule:
            self._load(rule)
            if getattr(rule, "is_system", False):
                self.name.setReadOnly(True)
                self.name.setToolTip(t('ui.rules_widget.systemregel_name_bleibt_stabil_damit_der_seed_be_fe13d56c'))

    def _setup(self):
        root = QVBoxLayout(self)
        fl = QFormLayout()
        fl.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.name = QLineEdit()
        self.desc = QTextEdit(); self.desc.setMaximumHeight(90)
        self.type = QComboBox(); self.type.addItems(["soft", "hard", "preference", "context"])
        self.group = QComboBox(); [self.group.addItem(_rule_group_label(key), key) for key in GROUP_ORDER]
        self.auto_action = QComboBox(); self.auto_action.addItems(["allow", "warn", "reject", "require_override"])
        self.warn = QComboBox(); self.warn.addItems(["info", "warning", "critical", "blocked"])
        self.score_delta = QLineEdit()
        self.score_delta.setPlaceholderText(t('ui.rules_widget.leer_automatisch_nach_warnstufe_z_b_30_oder_15_79e8f4bb'))
        self.cond = QComboBox()
        for key in CONDITION_KEYS:
            self.cond.addItem(_condition_label(key), key)
        self.template = QComboBox()
        self.template.addItem(t('ui.rules_widget.vorlage_wahlen_8ad1309e'), None)
        self.template.addItem(t('ui.rules_widget.vac_shimmer_vermeiden_11c5801a'), t('ui.rules_widget.fill_system_vac_prop_has_shimmer_value_true_b36811ba'))
        self.template.addItem(t('ui.rules_widget.grail_shimmer_kritisch_27e65410'), t('ui.rules_widget.tag_grail_prop_has_shimmer_value_true_f79f142c'))
        self.template.addItem(t('ui.rules_widget.ef_braucht_nasse_tinte_d2b18df1'), t('ui.rules_widget.nib_size_ef_wetness_min_4_d66f1287'))
        self.template.addItem(t('ui.rules_widget.pigment_kurzer_reinigen_38c023a4'), t('ui.rules_widget.prop_is_pigment_value_true_f0ab96b3'))
        self.template.currentIndexChanged.connect(self._apply_template)
        self.data_edit = QTextEdit()
        self.data_edit.setPlaceholderText(t('ui.rules_widget.parameter_werden_uber_vorlagen_gefullt_fortgesch_3983eaa1'))
        self.active = QCheckBox(t('ui.rules_widget.aktiv_220e3dbb'))
        self.active.setChecked(True)
        for label, widget in [
            ("Name", self.name),
            (t("rules.description_label"), self.desc),
            (t("ui.rules_widget.gruppe_b13e0a2f"), self.group),
            (t("ui.rules_widget.typ_e9038577"), self.type),
            (t("rules.warn_level"), self.warn),
            (t("ui.rules_widget.score_delta_label"), self.score_delta),
            (t("ui.rules_widget.auto_action_label"), self.auto_action),
            (t("ui.rules_widget.bedingung"), self.cond),
            (t("ui.rules_widget.vorlage"), self.template),
            (t("ui.rules_widget.parameter"), self.data_edit),
            ("", self.active),
        ]:
            fl.addRow(label + ":" if label else "", widget)
        root.addLayout(fl)
        help_label = QLabel(
            t('ui.rules_widget.einfachmodus_vorlage_wahlen_name_warnstufe_prufe_9ee744c1')
        )
        help_label.setWordWrap(True)
        root.addWidget(help_label)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _apply_template(self):
        data = self.template.currentData()
        if data:
            self.data_edit.setPlainText(data)
            text = self.template.currentText()
            if not self.name.text().strip():
                self.name.setText(text)
            if "Vac" in text:
                self.cond.setCurrentIndex(max(0, self.cond.findData("fill_system_ink_prop")))
                self.group.setCurrentIndex(max(0, self.group.findData("ink_fill")))
            elif "Grail" in text:
                self.cond.setCurrentIndex(max(0, self.cond.findData("pen_tag_ink_prop")))
                self.group.setCurrentIndex(max(0, self.group.findData("collector")))
            elif "EF" in text:
                self.cond.setCurrentIndex(max(0, self.cond.findData("nib_size_wetness")))
                self.group.setCurrentIndex(max(0, self.group.findData("nib")))
            elif "Pigment" in text:
                self.cond.setCurrentIndex(max(0, self.cond.findData("ink_prop_warning")))
                self.group.setCurrentIndex(max(0, self.group.findData("maintenance")))

    def _load(self, rule):
        self.name.setText(rule.name or "")
        self.desc.setPlainText(rule.description or "")
        self.group.setCurrentIndex(max(0, self.group.findData(getattr(rule, "rule_group", "") or "rotation")))
        self.type.setCurrentText(rule.rule_type or "soft")
        self.warn.setCurrentText(rule.warn_level or "info")
        delta = getattr(rule, "score_delta", None)
        self.score_delta.setText("" if delta is None else str(delta))
        self.auto_action.setCurrentText(getattr(rule, "auto_action", "") or "warn")
        self.active.setChecked(bool(rule.is_active))
        ix = self.cond.findData(rule.condition_type)
        self.cond.setCurrentIndex(max(0, ix))
        self.data_edit.setPlainText(rule.condition_data or "{}")

    def _save(self):
        if not self.name.text().strip():
            QMessageBox.warning(self, t('ui.rules_widget.pflichtfeld_b68af979'), t('ui.rules_widget.name_fehlt_4b1aa971'))
            return
        try:
            json.loads(self.data_edit.toPlainText() or "{}")
        except Exception as exc:
            QMessageBox.warning(self, t('ui.rules_widget.json_fehler_7c6ccea5'), str(exc))
            return
        delta = self.score_delta.text().strip()
        if delta:
            try:
                int(delta)
            except ValueError:
                QMessageBox.warning(self, t('ui.rules_widget.score_delta_24083dce'), t('ui.rules_widget.score_delta_muss_eine_ganze_zahl_sein_oder_leer__857a940d'))
                return
        self.accept()

    def data(self):
        delta_text = self.score_delta.text().strip()
        return {
            "name": self.name.text().strip(),
            "description": self.desc.toPlainText().strip() or None,
            "rule_group": self.group.currentData() or "rotation",
            "rule_type": self.type.currentText(),
            "warn_level": self.warn.currentText(),
            "score_delta": int(delta_text) if delta_text else None,
            "auto_action": self.auto_action.currentText(),
            "condition_type": self.cond.currentData(),
            "condition_data": self.data_edit.toPlainText().strip() or "{}",
            "is_active": self.active.isChecked(),
            "is_system": False if not self.rule else self.rule.is_system,
        }
