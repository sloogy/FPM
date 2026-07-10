"""
Einstellungen – Sprache, EDC-Slots, Datenbankpfad, Backup.

v0.2.4 – Änderbarer Datenbankpfad:
- Pfad kann per Dialog geändert werden (neue DB oder vorhandene öffnen).
- Aktuelle Daten können optional in die neue DB kopiert werden.
- reinit_db() wird direkt aufgerufen – kein Neustart nötig.
- Alle Widgets werden nach dem Wechsel automatisch aktualisiert.
"""
import csv
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox, QFormLayout, QComboBox, QSpinBox, QLineEdit, QFileDialog, QMessageBox, QApplication, QDialog, QDialogButtonBox, QRadioButton, QButtonGroup, QDoubleSpinBox, QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView, QStackedWidget, QListWidget, QListWidgetItem, QScrollArea, QFrame, QSizePolicy, QAbstractItemView
from PySide6.QtCore import Qt, Signal
from app_info import APP_VERSION
from database.db import get_session, get_db_path, reinit_db, set_db_path, reset_inkloads, reset_ink_levels, reset_pen_status, factory_reset_userdata
from i18n.translator import REGION_PRESETS, DEFAULT_EXCHANGE_RATES, DATE_FORMAT_OPTIONS, LocaleService, Translator, t
from i18n.qt_i18n import apply_widget_tree, translate_source_text
from database.models import AppSettings, Pen, Ink, Nib, Paper, InkLoad, Expense
from logic.budget_export_service import export_expenses_jsonl, default_budgetmanager_to_fpm_path, existing_fpm_bridge_ids, import_budgetmanager_proposals, load_budgetmanager_expense_proposals, sync_default_outbox_from_session
from ui.navigation import NavigationSettingsDialog
from logic.app_mode import APP_MODE_KEY, EXPERT_MODE, SIMPLE_MODE, get_app_mode, normalize_app_mode
from ui.ui_scale import PRESETS, apply_ui_scaling, scale_px

def _refresh_all_widgets():
    """Ruft refresh() auf allen Stack-Seiten des MainWindow auf."""
    for win in QApplication.topLevelWidgets():
        stack = getattr(win, '_stack', None)
        if stack is None:
            continue
        for i in range(stack.count()):
            w = stack.widget(i)
            if hasattr(w, 'refresh'):
                try:
                    w.refresh()
                except Exception:
                    pass
        for i in range(stack.count()):
            settings_w = stack.widget(i)
            if hasattr(settings_w, '_update_path_label'):
                settings_w._update_path_label()

class DbPathDialog(QDialog):
    """
    Erlaubt dem Nutzer:
      A) Neue leere Datenbank an einem frei wählbaren Ort anlegen.
      B) Vorhandene Datenbankdatei öffnen.

    In beiden Fällen kann er wählen, ob die aktuellen Daten kopiert werden.
    """

    def __init__(self, current_path: Path, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t('ui.settings_widget.datenbankpfad_andern_e03bd795'))
        self.setMinimumWidth(scale_px(520))
        self.setModal(True)
        self._current_path = current_path
        self._new_path: Path | None = None
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        info = QLabel(t('ui.settings_widget.current_db_path_html', path=current_path))
        info.setWordWrap(True)
        layout.addWidget(info)
        mode_grp = QGroupBox(t('ui.settings_widget.was_mochtest_du_tun_3c2ef2c3'))
        mode_layout = QVBoxLayout(mode_grp)
        self._mode_group = QButtonGroup(self)
        self._rb_new = QRadioButton(t('ui.settings_widget.neue_leere_datenbank_anlegen_frisch_starten_a4a8f845'))
        self._rb_open = QRadioButton(t('ui.settings_widget.vorhandene_datenbankdatei_offnen_wechseln_96515b61'))
        self._rb_new.setChecked(True)
        for rb in (self._rb_new, self._rb_open):
            self._mode_group.addButton(rb)
            mode_layout.addWidget(rb)
        layout.addWidget(mode_grp)
        path_row = QHBoxLayout()
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText(t('ui.settings_widget.pfad_zur_datenbankdatei_e4efe81d'))
        self._path_edit.setReadOnly(True)
        browse_btn = QPushButton(t('ui.settings_widget.durchsuchen_24ee1a3c'))
        browse_btn.setMinimumWidth(scale_px(150))
        browse_btn.clicked.connect(self._browse)
        path_row.addWidget(self._path_edit)
        path_row.addWidget(browse_btn)
        layout.addLayout(path_row)
        copy_grp = QGroupBox(t('ui.settings_widget.datenmigration_07427c01'))
        copy_layout = QVBoxLayout(copy_grp)
        self._copy_group = QButtonGroup(self)
        self._rb_copy = QRadioButton(t('ui.settings_widget.aktuelle_daten_in_neue_datenbank_kopieren_9a21a3f1'))
        self._rb_nocopy = QRadioButton(t('ui.settings_widget.neue_datenbank_leer_starten_nur_pfad_wechseln_ff88d340'))
        self._rb_copy.setChecked(True)
        for rb in (self._rb_copy, self._rb_nocopy):
            self._copy_group.addButton(rb)
            copy_layout.addWidget(rb)
        copy_note = QLabel(t('ui.settings_widget.i_beim_offnen_einer_vorhandenen_db_wird_nie_kopi_c1fd05ba'))
        copy_note.setStyleSheet('color:#7f8c8d; font-size:12px;')
        copy_note.setWordWrap(True)
        copy_layout.addWidget(copy_note)
        layout.addWidget(copy_grp)
        self._rb_open.toggled.connect(self._update_copy_state)
        self._update_copy_state()
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._validate_and_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _update_copy_state(self):
        """Kopier-Option deaktivieren wenn 'vorhandene DB öffnen' gewählt."""
        opening_existing = self._rb_open.isChecked()
        self._rb_copy.setEnabled(not opening_existing)
        self._rb_nocopy.setEnabled(not opening_existing)
        if opening_existing:
            self._rb_nocopy.setChecked(True)

    def _browse(self):
        if self._rb_new.isChecked():
            path, _ = QFileDialog.getSaveFileName(self, t('ui.settings_widget.neue_datenbankdatei_anlegen_5227515b'), str(Path.home() / 'fpm_sammlung.db'), t('ui.settings_widget.sqlite_datenbank_db_69bfc603'))
        else:
            path, _ = QFileDialog.getOpenFileName(self, t('ui.settings_widget.vorhandene_datenbankdatei_offnen_b2e0cb16'), str(Path.home()), t('ui.settings_widget.sqlite_datenbank_db_alle_dateien_7bf26a74'))
        if path:
            self._path_edit.setText(path)

    def _validate_and_accept(self):
        path_str = self._path_edit.text().strip()
        if not path_str:
            QMessageBox.warning(self, t('ui.settings_widget.kein_pfad_3c17c647'), t('ui.settings_widget.bitte_zuerst_einen_pfad_auswahlen_0994a51b'))
            return
        new_path = Path(path_str)
        if new_path == self._current_path:
            QMessageBox.information(self, t('ui.settings_widget.gleicher_pfad_b30e01f0'), t('ui.settings_widget.das_ist_bereits_der_aktuelle_pfad_a48c9978'))
            return
        self._new_path = new_path
        self.accept()

    @property
    def new_path(self) -> Path | None:
        return self._new_path

    @property
    def copy_data(self) -> bool:
        """True: aktuelle DB in neuen Pfad kopieren, dann dort öffnen."""
        return self._rb_copy.isChecked() and self._rb_new.isChecked()

class SettingsWidget(QWidget):
    tour_requested = Signal()

    def __init__(self):
        super().__init__()
        self._setup_ui()
        self._load()

    def _setup_ui(self):
        """Neue Settings-UI: linke Kategorien + rechter Scrollbereich.

        Die alte Einstellungsseite war eine lange Endlosliste. Mit wachsender App
        wird das unübersichtlich und erzeugt horizontale Quetschung. Diese Struktur
        trennt Optionen nach Themen und gibt jeder Kategorie ihren eigenen
        Scrollbalken.
        """
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)
        title = QLabel(t('ui.settings_widget.einstellungen_dfdfc9cc'))
        title.setObjectName('page_title')
        root.addWidget(title)
        hint = QLabel(t('ui.settings_widget.optionen_sind_nach_bereichen_getrennt_links_bere_e2a10495'))
        hint.setWordWrap(True)
        hint.setStyleSheet('color:#64748b; font-size:13px;')
        root.addWidget(hint)
        shell = QHBoxLayout()
        shell.setSpacing(14)
        root.addLayout(shell, 1)
        self.settings_nav = QListWidget()
        self.settings_nav.setObjectName('settingsNav')
        self.settings_nav.setFixedWidth(230)
        self.settings_nav.setSpacing(4)
        self.settings_nav.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.settings_nav.setStyleSheet('QListWidget#settingsNav { background:#ffffff; border:1px solid #d5dce6; border-radius:10px; padding:8px; outline:none; }QListWidget#settingsNav::item { padding:10px 12px; border-radius:7px; color:#334155; min-height:24px; }QListWidget#settingsNav::item:hover { background:#eef6ff; }QListWidget#settingsNav::item:selected { background:#2563eb; color:white; font-weight:700; }')
        self.settings_stack = QStackedWidget()
        self.settings_stack.setStyleSheet('QStackedWidget { background: transparent; }')
        shell.addWidget(self.settings_nav)
        shell.addWidget(self.settings_stack, 1)
        self._add_settings_page('Allgemein', '⚙', self._build_general_page())
        self._add_settings_page(t('settings.rotation_page_title'), '🎲', self._build_rotation_page())
        self._add_settings_page('Darstellung', '🔎', self._build_appearance_page())
        self._add_settings_page('Währung & Region', '🌍', self._build_currency_page())
        self._add_settings_page('Datenbank & Backup', '💾', self._build_database_page())
        self._add_settings_page('Import / Export', '📤', self._build_import_export_page())
        self._add_settings_page('Reset / Gefahrenzone', '⚠', self._build_reset_page())
        self._add_settings_page(t('settings.updates'), '⬆', self._build_update_page())
        self._add_settings_page('Über', 'ℹ', self._build_about_page())
        self.settings_nav.currentRowChanged.connect(self.settings_stack.setCurrentIndex)
        self.settings_nav.setCurrentRow(0)

    def _add_settings_page(self, title: str, icon: str, page: QWidget):
        item = QListWidgetItem(f'{icon}  {translate_source_text(title)}')
        self.settings_nav.addItem(item)
        self.settings_stack.addWidget(self._scroll_page(page))

    def _scroll_page(self, page: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setWidget(page)
        return scroll

    def _new_page(self, heading: str, text: str='') -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 0, 10, 18)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        h = QLabel(translate_source_text(heading))
        h.setStyleSheet('font-size:18px; font-weight:800; color:#1e293b;')
        layout.addWidget(h)
        if text:
            sub = QLabel(translate_source_text(text))
            sub.setWordWrap(True)
            sub.setStyleSheet('color:#64748b; font-size:13px;')
            layout.addWidget(sub)
        return (page, layout)

    def _form_card(self, title: str) -> tuple[QGroupBox, QFormLayout]:
        grp = QGroupBox(translate_source_text(title))
        fl = QFormLayout(grp)
        fl.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        fl.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        fl.setHorizontalSpacing(18)
        fl.setVerticalSpacing(10)
        return (grp, fl)

    def _v_card(self, title: str) -> tuple[QGroupBox, QVBoxLayout]:
        grp = QGroupBox(translate_source_text(title))
        layout = QVBoxLayout(grp)
        layout.setSpacing(10)
        return (grp, layout)

    def _note(self, text: str, kind: str='info') -> QLabel:
        colors = {'info': ('#eff6ff', '#bfdbfe', '#1d4ed8'), 'warn': ('#fffbeb', '#fde68a', '#92400e'), 'danger': ('#fef2f2', '#fecaca', '#991b1b'), 'ok': ('#ecfdf5', '#bbf7d0', '#166534')}
        bg, border, fg = colors.get(kind, colors['info'])
        lbl = QLabel(translate_source_text(text))
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f'background:{bg}; border:1px solid {border}; color:{fg}; border-radius:8px; padding:10px 12px; font-size:13px;')
        return lbl

    def _styled_button(self, text: str, kind: str='primary') -> QPushButton:
        palette = {'primary': '#2563eb', 'success': '#27ae60', 'secondary': '#7f8c8d', 'warning': '#f39c12', 'purple': '#8e44ad', 'danger': '#c0392b'}
        color = palette.get(kind, palette['primary'])
        b = QPushButton(translate_source_text(text))
        b.setStyleSheet(f'background:{color}; color:white; border:none; padding:8px 16px; border-radius:6px; font-weight:bold;')
        b.setMinimumHeight(scale_px(34))
        return b

    def _build_general_page(self) -> QWidget:
        page, root = self._new_page(t('ui.settings_widget.legacy_exact.text_001'), t('ui.settings_widget.general_page_body'))
        app_grp, app_fl = self._form_card(t('ui.settings_widget.legacy_exact.text_008'))
        self.lang_combo = QComboBox()
        self.lang_combo.addItem(t('ui.settings_widget.deutsch_60d0d336'), 'de')
        self.lang_combo.addItem(t('ui.settings_widget.english_8bbce4b7'), 'en')
        self.lang_combo.addItem(t('ui.settings_widget.francais_d8b98bd8'), 'fr')
        app_fl.addRow(t('ui.settings_widget.sprache_f5476699'), self.lang_combo)
        self.slots_spin = QSpinBox()
        self.slots_spin.setRange(1, 20)
        self.slots_spin.setValue(5)
        app_fl.addRow(t('ui.settings_widget.standard_edc_platze_713a7faf'), self.slots_spin)
        # Budgetgrenzen (0 = kein Limit); Anzeige/Ampel in der Statistik.
        self.budget_month_spin = QDoubleSpinBox()
        self.budget_month_spin.setRange(0.0, 1_000_000.0)
        self.budget_month_spin.setDecimals(2)
        self.budget_month_spin.setSpecialValueText(t("settings.budget_no_limit"))
        app_fl.addRow(t("settings.budget_monthly"), self.budget_month_spin)
        self.budget_year_spin = QDoubleSpinBox()
        self.budget_year_spin.setRange(0.0, 10_000_000.0)
        self.budget_year_spin.setDecimals(2)
        self.budget_year_spin.setSpecialValueText(t("settings.budget_no_limit"))
        app_fl.addRow(t("settings.budget_yearly"), self.budget_year_spin)
        self.app_mode_combo = QComboBox()
        self.app_mode_combo.addItem(t('settings.mode_simple'), SIMPLE_MODE)
        self.app_mode_combo.addItem(t('settings.mode_expert'), EXPERT_MODE)
        self.app_mode_combo.setToolTip(t('settings.mode_tooltip'))
        app_fl.addRow(t('settings.mode_label'), self.app_mode_combo)
        nav_btn = self._styled_button(t('ui.settings_widget.legacy_exact.text_009'), 'secondary')
        nav_btn.clicked.connect(self._edit_navigation)
        app_fl.addRow(t('ui.settings_widget.sidebar_kategorien_36e4d26d'), nav_btn)
        root.addWidget(app_grp)
        root.addWidget(self._note(t('ui.settings_widget.rules_module_note')))
        save_btn = self._styled_button(t('ui.settings_widget.legacy_exact.text_010'), 'primary')
        save_btn.setMinimumWidth(scale_px(330))
        save_btn.clicked.connect(self._save)
        root.addWidget(save_btn)
        root.addStretch(1)
        return page

    def _build_rotation_page(self) -> QWidget:
        """v0.2.80: Rotations-Verhalten zentral und erklärt einstellbar.

        Zufälligkeit als Prozentregler (0 = reine Bewertung, 100 = echter
        Zufall unter sicheren Kandidaten); dazu das bisher nur in der
        Datenbank versteckte Duplikat-Setting sichtbar als Checkbox.
        """
        page, root = self._new_page(t('settings.rotation_page_title'), t('settings.rotation_page_body'))
        rot_grp, rot_fl = self._form_card(t('settings.rotation_group_title'))
        self.rotation_random_spin = QSpinBox()
        self.rotation_random_spin.setRange(0, 100)
        self.rotation_random_spin.setSingleStep(5)
        self.rotation_random_spin.setSuffix(' %')
        self.rotation_random_spin.setToolTip(t('settings.rotation_random_tooltip'))
        rot_fl.addRow(t('settings.rotation_random_label'), self.rotation_random_spin)

        self.rotation_duplicates_cb = QCheckBox(t('settings.rotation_allow_duplicates'))
        self.rotation_duplicates_cb.setToolTip(t('settings.rotation_allow_duplicates_tooltip'))
        rot_fl.addRow('', self.rotation_duplicates_cb)

        root.addWidget(rot_grp)
        root.addWidget(self._note(t('settings.rotation_random_note'), 'warn'))
        root.addWidget(self._note(t('settings.rotation_reroll_note')))
        save_btn = self._styled_button(t('settings.rotation_save'), 'primary')
        save_btn.setMinimumWidth(scale_px(330))
        save_btn.clicked.connect(self._save_rotation_settings)
        root.addWidget(save_btn)
        root.addStretch(1)
        return page

    def _save_rotation_settings(self):
        session = get_session()
        try:
            AppSettings.set(session, 'rotation_randomness_percent', str(self.rotation_random_spin.value()))
            AppSettings.set(session, 'rotation_allow_active_ink_duplicates', '1' if self.rotation_duplicates_cb.isChecked() else '0')
            _refresh_all_widgets()
            QMessageBox.information(self, t('ui.settings_widget.gespeichert_28cb30ac'), t('settings.rotation_saved'))
        finally:
            session.close()

    def _build_appearance_page(self) -> QWidget:
        page, root = self._new_page(t('ui.settings_widget.legacy_exact.text_002'), t('ui.settings_widget.appearance_page_body'))
        ui_grp, ui_fl = self._form_card(t('ui.settings_widget.legacy_exact.text_011'))
        self.ui_scale_combo = QComboBox()
        for preset in PRESETS:
            self.ui_scale_combo.addItem(preset.label, preset.key)
        ui_fl.addRow(t('ui.settings_widget.ui_groe_6d78e564'), self.ui_scale_combo)
        info = QLabel(t('ui.settings_widget.auf_laptop_hidpi_meistens_auto_oder_laptop_gro_d_fbccac54'))
        info.setWordWrap(True)
        ui_fl.addRow(t('ui.settings_widget.empfehlung_6c4a25d1'), info)
        root.addWidget(ui_grp)
        apply_btn = self._styled_button(t('ui.settings_widget.legacy_exact.text_012'), 'primary')
        apply_btn.clicked.connect(self._save_appearance)
        root.addWidget(apply_btn)
        root.addWidget(self._note(t('ui.settings_widget.rules_density_note'), 'info'))
        root.addStretch(1)
        return page

    def _build_currency_page(self) -> QWidget:
        page, root = self._new_page(t('ui.settings_widget.legacy_exact.text_003'), t('ui.settings_widget.currency_region_page_body'))
        region_grp, region_fl = self._form_card(t('ui.settings_widget.legacy_exact.text_013'))
        self.region_combo = QComboBox()
        for code, preset in REGION_PRESETS.items():
            self.region_combo.addItem(preset['label'], code)
        self.region_combo.currentIndexChanged.connect(self._apply_region_preset)
        region_fl.addRow(t('ui.settings_widget.region_voreinstellung_36790b5e'), self.region_combo)
        self.currency_combo = QComboBox()
        for cur in ['CHF', 'EUR', 'USD', 'GBP']:
            self.currency_combo.addItem(cur, cur)
        region_fl.addRow(t('ui.settings_widget.standardwahrung_b11e6a73'), self.currency_combo)
        self.date_format_combo = QComboBox()
        for fmt, example in DATE_FORMAT_OPTIONS.items():
            self.date_format_combo.addItem(f'{fmt}  ({example})', fmt)
        region_fl.addRow(t('ui.settings_widget.date_format_label'), self.date_format_combo)
        dec_row = QHBoxLayout()
        self.dec_point_rb = QRadioButton(t('ui.settings_widget.punkt_1_234_56_4daf83b0'))
        self.dec_comma_rb = QRadioButton(t('ui.settings_widget.komma_1_234_56_ea863434'))
        self.dec_point_rb.setChecked(True)
        dec_row.addWidget(self.dec_point_rb)
        dec_row.addWidget(self.dec_comma_rb)
        dec_row.addStretch()
        region_fl.addRow(t('ui.settings_widget.dezimaltrennzeichen_fac776e8'), dec_row)
        thou_row = QHBoxLayout()
        self.thou_apos_rb = QRadioButton(t('ui.settings_widget.apostroph_1_234_3ed2e7fe'))
        self.thou_dot_rb = QRadioButton(t('ui.settings_widget.punkt_1_234_3ef398cc'))
        self.thou_comma_rb = QRadioButton(t('ui.settings_widget.komma_1_234_231b46e3'))
        self.thou_none_rb = QRadioButton(t('ui.settings_widget.keines_1234_eadbf854'))
        self.thou_apos_rb.setChecked(True)
        for rb in (self.thou_apos_rb, self.thou_dot_rb, self.thou_comma_rb, self.thou_none_rb):
            thou_row.addWidget(rb)
        thou_row.addStretch()
        region_fl.addRow(t('ui.settings_widget.tausendertrennzeichen_0162cb70'), thou_row)
        self.locale_preview = QLabel()
        self.locale_preview.setStyleSheet('color:#2563eb; font-weight:bold; font-size:14px;')
        region_fl.addRow(t('ui.settings_widget.vorschau_57ca03ef'), self.locale_preview)
        for w in (self.dec_point_rb, self.dec_comma_rb, self.thou_apos_rb, self.thou_dot_rb, self.thou_comma_rb, self.thou_none_rb):
            w.toggled.connect(self._update_locale_preview)
        self.currency_combo.currentIndexChanged.connect(self._update_locale_preview)
        self.date_format_combo.currentIndexChanged.connect(self._update_locale_preview)
        root.addWidget(region_grp)
        fx_grp, fx_layout = self._v_card(t('ui.settings_widget.legacy_exact.text_014'))
        fx_layout.addWidget(QLabel(t('ui.settings_widget.kurse_werden_fur_die_umrechnung_des_sammlungswer_f079130f')))
        self.fx_table = QTableWidget(len(DEFAULT_EXCHANGE_RATES) - 1, 2)
        self.fx_table.setHorizontalHeaderLabels([t('ui.settings_widget.wahrung_150ec8df'), t('ui.settings_widget.1_chf_einheiten_255cc6e7')])
        self.fx_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.fx_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.fx_table.setMinimumHeight(scale_px(150))
        self.fx_table.setMaximumHeight(scale_px(190))
        self.fx_table.verticalHeader().setVisible(False)
        self._fx_currencies = [c for c in DEFAULT_EXCHANGE_RATES if c != 'CHF']
        for row, cur in enumerate(self._fx_currencies):
            self.fx_table.setItem(row, 0, QTableWidgetItem(cur))
            self.fx_table.item(row, 0).setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.fx_table.setItem(row, 1, QTableWidgetItem(str(DEFAULT_EXCHANGE_RATES[cur])))
        fx_layout.addWidget(self.fx_table)
        fx_save_btn = self._styled_button(t('ui.settings_widget.legacy_exact.text_015'), 'success')
        fx_save_btn.clicked.connect(self._save_region_and_fx)
        fx_layout.addWidget(fx_save_btn)
        root.addWidget(fx_grp)
        root.addStretch(1)
        return page

    def _build_database_page(self) -> QWidget:
        page, root = self._new_page(t('ui.settings_widget.legacy_exact.text_004'), t('ui.settings_widget.legacy_exact.text_017'))
        db_grp, db_fl = self._form_card(t('settings.db_path'))
        path_row = QHBoxLayout()
        self.db_path_lbl = QLabel(str(get_db_path()))
        self.db_path_lbl.setStyleSheet('color:#2563eb; font-size:12px;')
        self.db_path_lbl.setWordWrap(True)
        self.db_path_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        change_path_btn = self._styled_button(t('ui.settings_widget.legacy_exact.text_018'), 'primary')
        change_path_btn.setMinimumWidth(scale_px(170))
        change_path_btn.clicked.connect(self._change_db_path)
        path_row.addWidget(self.db_path_lbl, 1)
        path_row.addWidget(change_path_btn)
        db_fl.addRow(t('ui.settings_widget.aktueller_pfad_559e89e2'), path_row)
        root.addWidget(db_grp)
        actions_grp, actions_layout = self._v_card(t('ui.settings_widget.legacy_exact.text_019'))
        db_btns = QHBoxLayout()
        for label, kind, slot in [('💾  Backup', 'success', self._backup), ('📂  Ordner öffnen', 'secondary', self._open_data_folder), ('🧹  Optimieren', 'purple', self._vacuum)]:
            b = self._styled_button(label, kind)
            b.clicked.connect(slot)
            db_btns.addWidget(b)
        db_btns.addStretch(1)
        actions_layout.addLayout(db_btns)
        root.addWidget(actions_grp)
        root.addWidget(self._note(t('ui.settings_widget.legacy_exact.text_023'), 'warn'))
        root.addStretch(1)
        return page

    def _build_import_export_page(self) -> QWidget:
        page, root = self._new_page(t('ui.settings_widget.legacy_exact.text_005'), t('ui.settings_widget.legacy_exact.text_025'))
        exp_grp, exp_layout = self._v_card(t('ui.settings_widget.csv_export_0c85e0e9'))
        exp_layout.addWidget(QLabel(t('ui.settings_widget.exportiert_fuller_tinten_federn_papier_inkloads__b6fe904d')))
        export_btn = self._styled_button(t('ui.settings_widget.legacy_exact.text_026'), 'warning')
        export_btn.setMinimumWidth(scale_px(240))
        export_btn.clicked.connect(self._export_csv)
        exp_layout.addWidget(export_btn)
        root.addWidget(exp_grp)

        bm_grp, bm_layout = self._v_card(t('settings.budget_export_title'))
        bm_text = QLabel(t('settings.budget_export_body'))
        bm_text.setWordWrap(True)
        bm_layout.addWidget(bm_text)
        bm_btn = self._styled_button(t('settings.budget_export_button'), 'success')
        bm_btn.setMinimumWidth(scale_px(280))
        bm_btn.clicked.connect(self._export_budgetmanager_jsonl)
        bm_layout.addWidget(bm_btn)
        bm_import_btn = self._styled_button(t('settings.budget_import_button'), 'primary')
        bm_import_btn.setMinimumWidth(scale_px(280))
        bm_import_btn.clicked.connect(self._import_budgetmanager_jsonl)
        bm_layout.addWidget(bm_import_btn)
        root.addWidget(bm_grp)

        root.addWidget(self._note(t('ui.settings_widget.legacy_exact.text_027')))
        root.addStretch(1)
        return page

    def _build_reset_page(self) -> QWidget:
        page, root = self._new_page(t('ui.settings_widget.legacy_exact.text_006'), t('ui.settings_widget.legacy_exact.text_028'))
        targeted_grp, targeted_layout = self._v_card(t('ui.settings_widget.legacy_exact.text_029'))
        targeted_layout.addWidget(QLabel(t('ui.settings_widget.datensatze_bleiben_erhalten_nur_bestimmte_status_a31f774c')))
        btn_row_r = QHBoxLayout()
        for text, tooltip, slot in [(t('ui.settings_widget.reset_inkloads_button'), t('ui.settings_widget.reset_inkloads_tooltip'), self._reset_inkloads), (t('ui.settings_widget.reset_ink_levels_button'), t('ui.settings_widget.reset_ink_levels_tooltip'), self._reset_ink_levels), (t('ui.settings_widget.reset_pen_status_button'), t('ui.settings_widget.reset_pen_status_tooltip'), self._reset_pen_status), (t('tour.triggers.reset_button'), t('tour.triggers.reset_tooltip'), self._reset_onboarding), (t('tour.triggers.start_now_button'), t('tour.triggers.start_now_tooltip'), self._start_tour_now)]:
            b = self._styled_button(text, 'secondary' if slot in (self._reset_onboarding, self._start_tour_now) else 'warning')
            b.setToolTip(translate_source_text(tooltip))
            b.clicked.connect(slot)
            btn_row_r.addWidget(b)
        btn_row_r.addStretch(1)
        targeted_layout.addLayout(btn_row_r)
        root.addWidget(targeted_grp)
        danger_grp, danger_layout = self._v_card(t('ui.settings_widget.factory_reset_76aece51'))
        danger_grp.setStyleSheet('QGroupBox { border: 1px solid #ef4444; background:#fff; }')
        danger_layout.addWidget(self._note(t('ui.settings_widget.legacy_exact.text_037'), 'danger'))
        btn_factory = self._styled_button(t('ui.settings_widget.legacy_exact.text_038'), 'danger')
        btn_factory.clicked.connect(self._factory_reset)
        danger_layout.addWidget(btn_factory)
        root.addWidget(danger_grp)
        root.addStretch(1)
        return page

    def _build_update_page(self) -> QWidget:
        page, root = self._new_page(t('settings.updates'), t('update.settings_body'))
        update_grp, update_layout = self._v_card(t('update.settings_group'))
        info = QLabel(t('update.settings_explain'))
        info.setWordWrap(True)
        update_layout.addWidget(info)
        btn = self._styled_button(t('update.btn_check'), 'primary')
        btn.setMinimumWidth(scale_px(260))
        btn.clicked.connect(self._open_update_dialog)
        update_layout.addWidget(btn)
        root.addWidget(update_grp)
        root.addWidget(self._note(t('update.settings_manifest_note'), 'warn'))
        root.addStretch(1)
        return page

    def _open_update_dialog(self):
        from ui.update_dialog import UpdateDialog
        UpdateDialog(self).exec()

    def _build_about_page(self) -> QWidget:
        page, root = self._new_page(t('settings.about'), t('ui.settings_widget.legacy_exact.text_040'))
        about_grp, about_fl = self._form_card(t('ui.settings_widget.legacy_exact.text_041'))
        about_fl.addRow(t('ui.settings_widget.version_75a25168'), QLabel(APP_VERSION))
        about_fl.addRow(t('ui.settings_widget.technologie_63a30fa2'), QLabel(t('ui.settings_widget.python_pyside6_sqlalchemy_sqlite_a914c1c5')))
        data_lbl = QLabel(t('ui.settings_widget.alle_daten_werden_lokal_gespeichert_keine_cloud__0812b031'))
        data_lbl.setWordWrap(True)
        about_fl.addRow(t('ui.settings_widget.daten_6c1d448f'), data_lbl)
        root.addWidget(about_grp)
        root.addWidget(self._note(t('ui.settings_widget.legacy_exact.text_042'), 'ok'))
        root.addStretch(1)
        return page

    def _update_path_label(self):
        self.db_path_lbl.setText(str(get_db_path()))

    def refresh(self):
        self._load()

    def _load(self):
        session = get_session()
        try:
            # v0.2.80: Rotations-Verhalten (Prozent-Zufall + Duplikate)
            if hasattr(self, 'rotation_random_spin'):
                try:
                    self.rotation_random_spin.setValue(int(float(AppSettings.get(session, 'rotation_randomness_percent', '0') or 0)))
                except (TypeError, ValueError):
                    self.rotation_random_spin.setValue(0)
            if hasattr(self, 'rotation_duplicates_cb'):
                allow_dup = str(AppSettings.get(session, 'rotation_allow_active_ink_duplicates', '0') or '0').lower() in {'1', 'true', 'yes', 'ja'}
                self.rotation_duplicates_cb.setChecked(allow_dup)
            lang = AppSettings.get(session, 'language', 'de')
            for i in range(self.lang_combo.count()):
                if self.lang_combo.itemData(i) == lang:
                    self.lang_combo.setCurrentIndex(i)
                    break
            region = AppSettings.get(session, 'locale_region', 'CH')
            for i in range(self.region_combo.count()):
                if self.region_combo.itemData(i) == region:
                    self.region_combo.setCurrentIndex(i)
                    break
            currency = AppSettings.get(session, 'default_currency', 'CHF')
            for i in range(self.currency_combo.count()):
                if self.currency_combo.itemData(i) == currency:
                    self.currency_combo.setCurrentIndex(i)
                    break
            date_format = AppSettings.get(session, 'locale_date_format', REGION_PRESETS.get(region, {}).get('date_format', 'DD.MM.YYYY'))
            for i in range(self.date_format_combo.count()):
                if self.date_format_combo.itemData(i) == date_format:
                    self.date_format_combo.setCurrentIndex(i)
                    break
            dec = AppSettings.get(session, 'locale_decimal_sep', '.')
            if dec == ',':
                self.dec_comma_rb.setChecked(True)
            else:
                self.dec_point_rb.setChecked(True)
            thou = AppSettings.get(session, 'locale_thousands_sep', "'")
            rb_map = {"'": self.thou_apos_rb, '.': self.thou_dot_rb, ',': self.thou_comma_rb, '': self.thou_none_rb}
            rb = rb_map.get(thou, self.thou_apos_rb)
            rb.setChecked(True)
            import json as _json
            rates_raw = AppSettings.get(session, 'exchange_rates_json')
            if rates_raw:
                rates = {**DEFAULT_EXCHANGE_RATES, **_json.loads(rates_raw)}
                for row, cur in enumerate(self._fx_currencies):
                    val = rates.get(cur, DEFAULT_EXCHANGE_RATES.get(cur, 1.0))
                    self.fx_table.item(row, 1).setText(str(val))
            self._update_locale_preview()
            slots = AppSettings.get(session, 'edc_slots', '5')
            try:
                self.budget_month_spin.setValue(float(AppSettings.get(session, 'budget_monthly', '0') or 0))
                self.budget_year_spin.setValue(float(AppSettings.get(session, 'budget_yearly', '0') or 0))
            except (TypeError, ValueError):
                self.budget_month_spin.setValue(0.0)
                self.budget_year_spin.setValue(0.0)
            self.slots_spin.setValue(int(slots))
            if hasattr(self, 'app_mode_combo'):
                ui_mode = get_app_mode()
                for i in range(self.app_mode_combo.count()):
                    if self.app_mode_combo.itemData(i) == ui_mode:
                        self.app_mode_combo.setCurrentIndex(i)
                        break
            if hasattr(self, 'ui_scale_combo'):
                ui_mode = AppSettings.get(session, 'ui_scale_mode', 'auto')
                for i in range(self.ui_scale_combo.count()):
                    if self.ui_scale_combo.itemData(i) == ui_mode:
                        self.ui_scale_combo.setCurrentIndex(i)
                        break
        finally:
            session.close()
        self._update_path_label()

    def _save_appearance(self):
        session = get_session()
        try:
            mode = self.ui_scale_combo.currentData() if hasattr(self, 'ui_scale_combo') else 'auto'
            AppSettings.set(session, 'ui_scale_mode', mode or 'auto')
            factor = apply_ui_scaling(QApplication.instance(), mode)
            for win in QApplication.topLevelWidgets():
                stack = getattr(win, '_stack', None)
                if stack is None:
                    continue
                for i in range(stack.count()):
                    w = stack.widget(i)
                    if hasattr(w, '_apply_scale'):
                        try:
                            w._apply_scale()
                        except Exception:
                            pass
                    if hasattr(w, 'refresh'):
                        try:
                            w.refresh()
                        except Exception:
                            pass
            QMessageBox.information(self, t('ui.settings_widget.darstellung_gespeichert_46986f29'), t('settings.ui_scale_saved_body', factor=f'{factor:.2f}'))
        finally:
            session.close()

    def _save(self):
        session = get_session()
        try:
            lang = self.lang_combo.currentData() or 'de'
            AppSettings.set(session, 'language', lang)
            AppSettings.set(session, 'edc_slots', str(self.slots_spin.value()))
            if hasattr(self, 'app_mode_combo'):
                new_mode = normalize_app_mode(self.app_mode_combo.currentData() or SIMPLE_MODE)
                AppSettings.set(session, APP_MODE_KEY, new_mode)
                for win in QApplication.topLevelWidgets():
                    sidebar = getattr(win, 'sidebar', None)
                    if sidebar is not None and hasattr(sidebar, '_setup_ui'):
                        try:
                            sidebar._setup_ui()
                            sidebar.modeChanged.emit(new_mode)
                        except Exception:
                            pass
            AppSettings.set(session, 'budget_monthly', f"{self.budget_month_spin.value():.2f}")
            AppSettings.set(session, 'budget_yearly', f"{self.budget_year_spin.value():.2f}")
            Translator.instance().set_language(lang)
            _refresh_all_widgets()
            for win in QApplication.topLevelWidgets():
                apply_widget_tree(win)
            QMessageBox.information(self, t('ui.settings_widget.gespeichert_28cb30ac'), t('ui.settings_widget.einstellungen_wurden_gespeichert_sprache_wurde_s_dbc1daea'))
        finally:
            session.close()

    def _apply_region_preset(self, _idx: int):
        """Regionsvoreinstellung: Felder automatisch befüllen."""
        code = self.region_combo.currentData()
        preset = REGION_PRESETS.get(code, {})
        cur = preset.get('currency', 'CHF')
        for i in range(self.currency_combo.count()):
            if self.currency_combo.itemData(i) == cur:
                self.currency_combo.setCurrentIndex(i)
                break
        if preset.get('decimal_sep') == ',':
            self.dec_comma_rb.setChecked(True)
        else:
            self.dec_point_rb.setChecked(True)
        thou_map = {"'": self.thou_apos_rb, '.': self.thou_dot_rb, ',': self.thou_comma_rb, '': self.thou_none_rb}
        rb = thou_map.get(preset.get('thousands_sep', "'"), self.thou_apos_rb)
        rb.setChecked(True)
        fmt = preset.get('date_format', 'DD.MM.YYYY')
        for i in range(self.date_format_combo.count()):
            if self.date_format_combo.itemData(i) == fmt:
                self.date_format_combo.setCurrentIndex(i)
                break
        self._update_locale_preview()

    def _get_decimal_sep(self) -> str:
        return ',' if self.dec_comma_rb.isChecked() else '.'

    def _get_thousands_sep(self) -> str:
        if self.thou_apos_rb.isChecked():
            return "'"
        if self.thou_dot_rb.isChecked():
            return '.'
        if self.thou_comma_rb.isChecked():
            return ','
        return ''

    def _update_locale_preview(self):
        """Vorschau des aktuellen Zahlenformats."""
        dec = self._get_decimal_sep()
        thou = self._get_thousands_sep()
        cur = self.currency_combo.currentData() or 'CHF'
        fmt = self.date_format_combo.currentData() if hasattr(self, 'date_format_combo') else 'DD.MM.YYYY'
        num = '1{thou}234{dec}56'.format(thou=thou, dec=dec)
        date_example = str(fmt).replace('YYYY', '2026').replace('DD', '31').replace('MM', '12')
        self.locale_preview.setText(f'{cur} {num}   ·   {num} {cur}   ·   {date_example}')

    def _save_region_and_fx(self):
        """Region, Trennzeichen und Wechselkurse in AppSettings speichern."""
        import json as _json
        session = get_session()
        try:
            dec = self._get_decimal_sep()
            thou = self._get_thousands_sep()
            cur = self.currency_combo.currentData() or 'CHF'
            region = self.region_combo.currentData() or 'CH'
            date_format = self.date_format_combo.currentData() or REGION_PRESETS.get(region, {}).get('date_format', 'DD.MM.YYYY')
            AppSettings.set(session, 'default_currency', cur)
            AppSettings.set(session, 'locale_decimal_sep', dec)
            AppSettings.set(session, 'locale_thousands_sep', thou)
            AppSettings.set(session, 'locale_date_format', date_format)
            AppSettings.set(session, 'locale_region', region)
            AppSettings.set(session, 'locale_currency_position', REGION_PRESETS.get(region, {}).get('currency_position', 'before'))
            rates = {'CHF': 1.0}
            for row, fx_cur in enumerate(self._fx_currencies):
                item = self.fx_table.item(row, 1)
                try:
                    rates[fx_cur] = float((item.text() if item else '').replace(',', '.') or 1.0)
                except ValueError:
                    rates[fx_cur] = DEFAULT_EXCHANGE_RATES.get(fx_cur, 1.0)
            AppSettings.set(session, 'exchange_rates_json', _json.dumps(rates))
            QMessageBox.information(self, t('ui.settings_widget.gespeichert_28cb30ac'), t('ui.settings_widget.region_saved_message', region=region, currency=cur))
            LocaleService.reset()
            _refresh_all_widgets()
        except Exception as e:
            QMessageBox.critical(self, t('ui.settings_widget.fehler_a1fcc21e'), str(e))
        finally:
            session.close()

    def _change_db_path(self):
        current = get_db_path()
        dlg = DbPathDialog(current, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        new_path = dlg.new_path
        copy_data = dlg.copy_data
        action_txt = t('ui.settings_widget.db_path_copy_action') if copy_data else t('ui.settings_widget.db_path_switch_action')
        reply = QMessageBox.question(self, t('ui.settings_widget.datenbankpfad_wirklich_andern_35c42065'), t('ui.settings_widget.db_path_confirm_message', path=new_path, action=action_txt), QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            if copy_data:
                new_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(current, new_path)
            reinit_db(new_path)
            _refresh_all_widgets()
            QMessageBox.information(self, t('ui.settings_widget.datenbankpfad_geandert_e744156e'), t('ui.settings_widget.db_path_changed_message', path=new_path, copied=t('ui.settings_widget.db_path_copied_suffix') if copy_data else ''))
        except Exception as e:
            QMessageBox.critical(self, t('ui.settings_widget.fehler_beim_pfadwechsel_9b0711c5'), t('ui.settings_widget.db_path_change_failed_message', error=e))

    def _backup(self):
        src = get_db_path()
        dest, _ = QFileDialog.getSaveFileName(self, t('ui.settings_widget.backup_speichern_ba303091'), str(Path.home() / 'fpm_backup.db'), t('ui.settings_widget.sqlite_db_fc737339'))
        if dest:
            shutil.copy2(src, dest)
            QMessageBox.information(self, t('ui.settings_widget.backup_5b11f811'), t('ui.settings_widget.backup_saved_message', path=dest))

    def _open_data_folder(self):
        folder = get_db_path().parent
        try:
            if sys.platform.startswith('linux'):
                subprocess.Popen(['xdg-open', str(folder)])
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', str(folder)])
            else:
                os.startfile(str(folder))
        except Exception as e:
            QMessageBox.warning(self, t('settings.folder_open_title'), t('settings.folder_open_err', error=e))

    def _vacuum(self):
        try:
            con = sqlite3.connect(get_db_path())
            con.execute('VACUUM')
            con.close()
            QMessageBox.information(self, t('ui.settings_widget.datenbank_a4f4bb1e'), t('ui.settings_widget.datenbank_wurde_optimiert_7b5372af'))
        except Exception as e:
            QMessageBox.critical(self, t('ui.settings_widget.fehler_a1fcc21e'), str(e))

    def _export_csv(self):
        folder = QFileDialog.getExistingDirectory(self, t('ui.settings_widget.csv_exportordner_wahlen_9cb9d70e'), str(Path.home()))
        if not folder:
            return
        folder = Path(folder)
        session = get_session()
        try:
            tables = {'pens.csv': session.query(Pen).all(), 'inks.csv': session.query(Ink).all(), 'nibs.csv': session.query(Nib).all(), 'papers.csv': session.query(Paper).all(), 'ink_loads.csv': session.query(InkLoad).all(), 'expenses.csv': session.query(Expense).all()}
            for filename, rows in tables.items():
                path = folder / filename
                if not rows:
                    path.write_text('', encoding='utf-8')
                    continue
                cols = [c.name for c in rows[0].__table__.columns]
                with path.open('w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(cols)
                    for row in rows:
                        writer.writerow([getattr(row, c) for c in cols])
            QMessageBox.information(self, t('ui.settings_widget.csv_export_0c85e0e9'), t('ui.settings_widget.csv_export_done', folder=folder))
        except Exception as e:
            QMessageBox.critical(self, t('ui.settings_widget.fehler_a1fcc21e'), str(e))
        finally:
            session.close()


    def _export_budgetmanager_jsonl(self):
        default_path = default_budgetmanager_to_fpm_path().with_name('fpm_to_budgetmanager_export.jsonl')
        dest, _ = QFileDialog.getSaveFileName(
            self,
            t('settings.budget_export_dialog_title'),
            str(default_path),
            t('settings.budget_export_file_filter'),
        )
        if not dest:
            return
        session = get_session()
        try:
            expenses = session.query(Expense).order_by(Expense.purchase_date.asc().nullslast(), Expense.id.asc()).all()
            result = export_expenses_jsonl(expenses, dest)
            sync_default_outbox_from_session(session)
            QMessageBox.information(
                self,
                t('settings.budget_export_done_title'),
                t(
                    'settings.budget_export_done_body',
                    count=result.count,
                    total=result.total,
                    currencies=', '.join(result.currencies) or '—',
                    path=result.path,
                ),
            )
        except Exception as e:
            QMessageBox.critical(self, t('ui.settings_widget.fehler_a1fcc21e'), str(e))
        finally:
            session.close()

    def _import_budgetmanager_jsonl(self):
        default_path = default_budgetmanager_to_fpm_path()
        src, _ = QFileDialog.getOpenFileName(
            self,
            t('settings.budget_import_dialog_title'),
            str(default_path),
            t('settings.budget_export_file_filter'),
        )
        if not src:
            return
        session = get_session()
        try:
            existing = existing_fpm_bridge_ids(session)
            proposals = load_budgetmanager_expense_proposals(src, existing_external_ids=existing)
            fresh = [p for p in proposals if not p.duplicate]
            duplicates = len(proposals) - len(fresh)
            if not proposals:
                QMessageBox.information(self, t('settings.budget_import_empty_title'), t('settings.budget_import_empty_body'))
                return
            total = round(sum(float(p.amount or 0.0) for p in fresh), 2)
            answer = QMessageBox.question(
                self,
                t('settings.budget_import_preview_title'),
                t(
                    'settings.budget_import_preview_body',
                    count=len(fresh),
                    duplicates=duplicates,
                    total=total,
                    path=src,
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            imported = import_budgetmanager_proposals(session, proposals)
            session.commit()
            sync_default_outbox_from_session(session)
            _refresh_all_widgets()
            QMessageBox.information(
                self,
                t('settings.budget_import_done_title'),
                t('settings.budget_import_done_body', count=imported),
            )
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, t('ui.settings_widget.fehler_a1fcc21e'), str(e))
        finally:
            session.close()

    def _edit_navigation(self):
        dlg = NavigationSettingsDialog(self)
        dlg.exec()

    def _reset_inkloads(self):
        res = QMessageBox.question(self, t('ui.settings_widget.inkloads_schlieen_9e80243a'), t('ui.settings_widget.alle_aktiven_inkloads_werden_auf_gereinigt_geset_91ebc62d'), QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if res != QMessageBox.StandardButton.Yes:
            return
        count = reset_inkloads(keep_history=True)
        QMessageBox.information(self, t('ui.settings_widget.erledigt_617fe081'), t('ui.settings_widget.inkloads_closed_done', count=count))
        _refresh_all_widgets()

    def _reset_ink_levels(self):
        res = QMessageBox.question(self, t('ui.settings_widget.tintenmengen_zurucksetzen_4adf4aa1'), t('ui.settings_widget.remaining_ml_aller_tinten_wird_auf_die_eingetrag_c1b59107'), QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if res != QMessageBox.StandardButton.Yes:
            return
        count = reset_ink_levels()
        QMessageBox.information(self, t('ui.settings_widget.erledigt_617fe081'), t('ui.settings_widget.ink_levels_reset_done', count=count))
        _refresh_all_widgets()

    def _reset_pen_status(self):
        res = QMessageBox.question(self, t('ui.settings_widget.fuller_status_zurucksetzen_2b938d23'), t('ui.settings_widget.alle_fuller_werden_auf_status_verfugbar_gesetzt__177d4e75'), QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if res != QMessageBox.StandardButton.Yes:
            return
        count = reset_pen_status()
        QMessageBox.information(self, t('ui.settings_widget.erledigt_617fe081'), t('ui.settings_widget.pen_status_reset_done', count=count))
        _refresh_all_widgets()

    def _start_tour_now(self):
        """Tour sofort starten.

        SettingsWidget selbst kennt das MainWindow nicht. Darum wird nur ein
        Signal gesendet; MainWindow verbindet dieses Signal mit start_tour().
        Verhindert den Runtime-Crash beim Öffnen der Einstellungen.
        """
        try:
            self.tour_requested.emit()
        except Exception as e:
            QMessageBox.warning(self, t('tour.triggers.title'), t('tour.triggers.start_error', error=e))

    def _reset_onboarding(self):
        """Onboarding-/Tour-Status zurücksetzen (Tour erscheint beim nächsten Start bei leerer DB)."""
        session = get_session()
        try:
            AppSettings.set(session, 'onboarding_completed', '0')
            session.commit()
        finally:
            session.close()
        QMessageBox.information(self, t('tour.triggers.reset_done_title'), t('tour.triggers.reset_done_body'))

    def _factory_reset(self):
        res1 = QMessageBox.warning(self, t('ui.settings_widget.factory_reset_36f5d701'), t('ui.settings_widget.achtung_diese_aktion_loscht_alle_fuller_tinten_f_80e88cda'), QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
        if res1 != QMessageBox.StandardButton.Yes:
            return
        res2 = QMessageBox.critical(self, t('ui.settings_widget.letzte_warnung_673d7f65'), t('ui.settings_widget.alle_nutzerdaten_werden_jetzt_geloscht_dies_kann_f80de1ed'), QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
        if res2 != QMessageBox.StandardButton.Yes:
            return
        try:
            factory_reset_userdata()
            QMessageBox.information(self, t('ui.settings_widget.factory_reset_76aece51'), t('ui.settings_widget.alle_nutzerdaten_wurden_geloscht_db379920'))
            _refresh_all_widgets()
        except Exception as e:
            QMessageBox.critical(self, t('ui.settings_widget.fehler_a1fcc21e'), str(e))
