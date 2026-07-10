"""
Rotations-Widget – Vorschläge übernehmen, Leeren empfehlen, Regeln sichtbar machen.

FIX v0.2.3:
- Code vollständig neu formatiert (war komplett in Einzeilern).
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QGroupBox, QSpinBox, QMessageBox, QMenu, QComboBox,
    QDialog, QDialogButtonBox, QProgressBar,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QAction

from logic.rotation_engine import RotationEngine
from ui.role_prefs_dialog import RolePrefsDialog
from logic.event_bus import AppEventBus
from ui.ui_scale import scale_px
from i18n.translator import t
from i18n.qt_i18n import translate_source_text


def _rotation_theme_options():
    return [
        (None,            t("rotation.theme_filter_auto")),
        ("edc",           t("rotation.theme_edc")),
        ("agenda",        t("rotation.theme_agenda")),
        ("journal",       t("rotation.theme_journal")),
        ("work",          t("rotation.theme_work")),
        ("creative",      t("rotation.theme_creative")),
        ("letter",        t("rotation.theme_letter")),
        ("archive",       t("rotation.theme_archive")),
        ("cheap_paper",   t("rotation.theme_cheap")),
        ("fine_nib",      t("rotation.theme_fine_nib")),
        ("broad_nib",     t("rotation.theme_broad_nib")),
        ("sheen_showcase",t("rotation.theme_sheen")),
        ("testing",       t("rotation.theme_testing")),
    ]
ROTATION_THEME_OPTIONS = _rotation_theme_options()


class RotationWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._engine = RotationEngine()
        self._last_suggestions: list = []   # Cache für Override-Dialog
        # v0.2.80: (Füller, Tinte)-Paare aus früheren Vorschlagsrunden.
        # Erneutes Klicken auf "Vorschläge" meidet diese Paare kumulativ,
        # damit jede Runde andere Tinten zeigt; dieselbe Tinte bleibt für
        # andere Füller verfügbar (Paar- statt Tintensperre).
        self._avoid_pairs: set[tuple[int, int]] = set()
        self._selected_paper_id: int | None = None
        self._selected_theme: str | None = None
        self._setup_ui()
        # EventBus: Rotation refresht wenn Füller oder Tinten geändert werden
        bus = AppEventBus.instance()
        bus.pens_changed.connect(self.refresh)
        bus.inks_changed.connect(self.refresh)
        bus.papers_changed.connect(self._reload_paper_dropdown)
        self.refresh()

    # ------------------------------------------------------------------ #
    # UI-Aufbau                                                           #
    # ------------------------------------------------------------------ #
    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(18)

        # ── Header ──────────────────────────────────────────────────
        hdr = QHBoxLayout()
        title = QLabel(t('ui.rotation_widget.intelligente_rotation_5b17626e'))
        title.setObjectName("page_title")
        hdr.addWidget(title)
        hdr.addStretch()

        # ── Papier-Kontext (Bug 5: Paper in Rotation) ────────────────
        hdr.addWidget(QLabel(t('ui.rotation_widget.papier_5b44bb18')))
        self.paper_combo = QComboBox()
        self.paper_combo.setMinimumWidth(scale_px(180))
        self.paper_combo.setToolTip(
            t('ui.rotation_widget.aktives_papier_beeinflusst_den_score_ef_hohes_fe_420facf3')
        )
        self.paper_combo.currentIndexChanged.connect(self._on_paper_changed)
        hdr.addWidget(self.paper_combo)

        hdr.addWidget(QLabel(t("ui.rotation_widget.theme_label_short")))
        self.theme_combo = QComboBox()
        self.theme_combo.setMinimumWidth(scale_px(180))
        self.theme_combo.setToolTip(t("rotation.theme_filter_tooltip"))
        for val, label in _rotation_theme_options():
            self.theme_combo.addItem(label, val)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        hdr.addWidget(self.theme_combo)
        _role_cfg_btn = QPushButton(t("rotation.role_edit_btn"))
        _role_cfg_btn.setFixedWidth(80)
        _role_cfg_btn.setToolTip(t("rotation.role_editor_hint"))
        _role_cfg_btn.clicked.connect(lambda: RolePrefsDialog(self).exec())
        hdr.addWidget(_role_cfg_btn)

        hdr.addWidget(QLabel(t('ui.rotation_widget.edc_platze_ab6de646')))
        self.slots_spin = QSpinBox()
        self.slots_spin.setRange(1, 30)
        self.slots_spin.setValue(5)
        hdr.addWidget(self.slots_spin)

        self.generate_btn = QPushButton(t("rotation.generate_button"))
        self.generate_btn.setToolTip(t("rotation.generate_tooltip"))
        self.generate_btn.setStyleSheet(
            "background:#9b59b6; color:white; border:none;"
            " padding:7px 14px; border-radius:5px; font-weight:bold;"
        )
        self.generate_btn.clicked.connect(self.generate_suggestions)
        hdr.addWidget(self.generate_btn)

        self.refresh_btn = QPushButton(t("rotation.refresh_button"))
        self.refresh_btn.setStyleSheet(
            "background:#3498db; color:white; border:none;"
            " padding:7px 14px; border-radius:5px; font-weight:bold;"
        )
        self.refresh_btn.clicked.connect(self.refresh)
        hdr.addWidget(self.refresh_btn)

        root.addLayout(hdr)

        # ── Aktuelle Belegung ────────────────────────────────────────
        cur_grp = QGroupBox(t('ui.rotation_widget.aktuelle_belegung_135de37c'))
        cur_layout = QVBoxLayout(cur_grp)

        self.cur_table = QTableWidget(0, 8)
        self.cur_table.setHorizontalHeaderLabels(
            [t('ui.rotation_widget.farbe_7fd6df73'), t('ui.rotation_widget.fuller_30e41efe'), t('ui.rotation_widget.tinte_0d292b04'), t('ui.rotation_widget.fullsystem_4a0a8d7e'), t('ui.rotation_widget.tage_0b499851'), t('ui.rotation_widget.max_45c1eb63'), t('ui.rotation_widget.score_316b6865'), t('ui.rotation_widget.hinweis_e423dc13')]
        )
        self._setup_table(self.cur_table, stretch_cols=(1, 2, 7))
        self._set_score_tooltip(self.cur_table, 6)  # Score = Spalte 6
        self.cur_table.setMaximumHeight(220)
        cur_layout.addWidget(self.cur_table)
        root.addWidget(cur_grp)

        # ── Vorschläge ───────────────────────────────────────────────
        sug_grp = QGroupBox(t('ui.rotation_widget.vorschlage_fur_leere_fuller_48573886'))
        sug_layout = QVBoxLayout(sug_grp)

        self.sug_info = QLabel(t('ui.rotation_widget.klicke_auf_vorschlage_um_empfehlungen_zu_laden_416b1745'))
        self.sug_info.setStyleSheet("color:#7f8c8d; font-style:italic; padding:8px;")
        sug_layout.addWidget(self.sug_info)

        score_info = QLabel(
            t('ui.rotation_widget.i_score_legende_leer_120_nicht_genutzt_tage_0_70_3dedf9e1')
        )
        score_info.setWordWrap(True)
        score_info.setStyleSheet(
            "background:#f0f7ff; border:1px solid #bdd7f5; border-radius:5px;"
            " padding:8px; color:#1e3a5f; font-size:11px;"
        )
        sug_layout.addWidget(score_info)

        self.sug_table = QTableWidget(0, 7)
        self.sug_table.setWordWrap(False)  # v0.2.80: einzeilige Vorschlagszeilen
        self.sug_table.setHorizontalHeaderLabels(
            [t('ui.rotation_widget.farbe_7fd6df73'), t('ui.rotation_widget.fuller_30e41efe'), t('ui.rotation_widget.tinte_0d292b04'), t('ui.rotation_widget.fullsystem_4a0a8d7e'), t('ui.rotation_widget.score_316b6865'), t('ui.rotation_widget.hinweise_281c0cb1'), t('ui.rotation_widget.aktion_2e14a645')]
        )
        self._setup_table(self.sug_table, stretch_cols=(1, 2, 5))
        self.sug_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.sug_table.customContextMenuRequested.connect(self._show_suggestion_menu)
        # Rechtsklick funktioniert je nach Wayland/Touchpad nicht immer zuverlässig.
        # Darum zusätzlich: Doppelklick auf eine Vorschlagszeile übernimmt direkt.
        self.sug_table.doubleClicked.connect(self._handle_suggestion_double_click)
        self.sug_table.cellClicked.connect(lambda row, col: self._maybe_show_why(self.sug_table.model().index(row, col)))
        self.sug_table.hide()
        sug_layout.addWidget(self.sug_table)
        root.addWidget(sug_grp)

        # ── Freie Tinten ─────────────────────────────────────────────
        free_grp = QGroupBox(t('ui.rotation_widget.freie_tinten_verfugbar_nicht_leer_nicht_aktuell__8a212760'))
        free_layout = QVBoxLayout(free_grp)
        self.free_table = QTableWidget(0, 6)
        self.free_table.setHorizontalHeaderLabels(
            [t('ui.rotation_widget.farbe_7fd6df73'), t('ui.rotation_widget.tinte_0d292b04'), t('ui.rotation_widget.farbfamilie_d86f5d6c'), t('ui.rotation_widget.rest_c5861809'), t('ui.rotation_widget.letzte_fullung_31b48d33'), t('ui.rotation_widget.sicherheit_2badd6c6')]
        )
        self._setup_table(self.free_table, stretch_cols=(1, 5))
        self.free_table.setMaximumHeight(180)
        free_layout.addWidget(self.free_table)
        root.addWidget(free_grp)

        # ── Leeren-Empfehlungen ──────────────────────────────────────
        clean_grp = QGroupBox(t('ui.rotation_widget.leeren_und_direkt_neu_befullen_2d17c8db'))
        clean_layout = QVBoxLayout(clean_grp)

        self.clean_table = QTableWidget(0, 7)
        self.clean_table.setHorizontalHeaderLabels(
            [t('ui.rotation_widget.fuller_30e41efe'), t('ui.rotation_widget.aktuelle_tinte_f3b8ee32'), t('ui.rotation_widget.score_316b6865'), t('ui.rotation_widget.empfehlung_ca7a499f'), t('ui.rotation_widget.neue_tinte_71d9ef61'), t('ui.rotation_widget.leeren_8e37cb14'), t('ui.rotation_widget.leeren_befullen_6fc57110')]
        )
        self._setup_table(self.clean_table, stretch_cols=(0, 1, 3, 4))
        clean_layout.addWidget(self.clean_table)
        root.addWidget(clean_grp)

        root.addStretch()

    def _set_score_tooltip(self, table: QTableWidget, col_idx: int):
        """Score-Spalte mit erklärendem Tooltip versehen."""
        item = table.horizontalHeaderItem(col_idx)
        if item:
            item.setToolTip(
                t('ui.rotation_widget.score_interne_gewichtung_der_rotation_hoher_bess_b09e85c8')
            )

    def _setup_table(self, t: QTableWidget, stretch_cols: tuple = ()):
        h = t.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        for c in stretch_cols:
            h.setSectionResizeMode(c, QHeaderView.ResizeMode.Stretch)
        t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t.setAlternatingRowColors(True)

    # ------------------------------------------------------------------ #
    # Refresh – aktuelle Rotation                                         #
    # ------------------------------------------------------------------ #
    def refresh(self):
        self._reload_paper_dropdown()
        data = self._engine.get_current_rotation()
        self.cur_table.setRowCount(len(data))

        for row, d in enumerate(data):
            color_item = QTableWidgetItem("")
            color_item.setBackground(QColor(d["color_hex"]))
            self.cur_table.setItem(row, 0, color_item)

            for col, key in enumerate(
                ["pen_name", "ink_name", "fill_system",
                 "days", "max_days", "score"], start=1
            ):
                self.cur_table.setItem(row, col, QTableWidgetItem(str(d[key])))

            hint_parts = []
            if d["overdue"]: hint_parts.append(translate_source_text("⚠ Reinigung fällig"))
            status = d.get("availability_status", "available")
            if status != "available": hint_parts.append(f"{translate_source_text("Status")}: {status}")
            if d.get("rotation_blocked"): hint_parts.append(translate_source_text("gesperrt"))
            if d["must"]:    hint_parts.append(translate_source_text("⭐ Pflicht"))
            if d["fixed"]:   hint_parts.append(translate_source_text("💍 verheiratet"))
            self.cur_table.setItem(row, 7, QTableWidgetItem(" | ".join(hint_parts) or "—"))

            if d["overdue"]:
                item = self.cur_table.item(row, 4)
                item.setForeground(QColor("#e74c3c"))
                item.setFont(QFont("", -1, QFont.Weight.Bold))

        if not data:
            self.cur_table.setRowCount(1)
            self.cur_table.setItem(0, 0, QTableWidgetItem(t('ui.rotation_widget.keine_fuller_mit_eingefullter_tinte_19f7af25')))
            self.cur_table.setSpan(0, 0, 1, 8)

        self._refresh_free_inks()
        self._refresh_cleaning()

    def _refresh_free_inks(self):
        rows = self._engine.get_free_inks()
        self.free_table.setRowCount(len(rows))
        for r, d in enumerate(rows):
            color_item = QTableWidgetItem("")
            color_item.setBackground(QColor(d.get("color_hex", "#888888")))
            self.free_table.setItem(r, 0, color_item)
            self.free_table.setItem(r, 1, QTableWidgetItem(d.get("name", "")))
            self.free_table.setItem(r, 2, QTableWidgetItem(d.get("color_family", "—")))
            rest = d.get("remaining_ml")
            self.free_table.setItem(r, 3, QTableWidgetItem(f"{rest:g} ml" if rest is not None else "—"))
            self.free_table.setItem(r, 4, QTableWidgetItem(d.get("last_loaded", "—")))
            self.free_table.setItem(r, 5, QTableWidgetItem(d.get("safety", "")))
        if not rows:
            self.free_table.setRowCount(1)
            self.free_table.setItem(0, 0, QTableWidgetItem(t('ui.rotation_widget.keine_freien_tinten_alle_verfugbaren_tinten_sind_4c365577')))
            self.free_table.setSpan(0, 0, 1, 6)

    # ------------------------------------------------------------------ #
    # Vorschläge generieren                                               #
    # ------------------------------------------------------------------ #
    def generate_suggestions(self) -> bool:
        """Öffentliche Aktion für Toolbar, Tour und normale UI."""
        return self._generate()

    def apply_first_suggestion(self) -> bool:
        """Ersten sichtbaren Vorschlag bewusst übernehmen (Tour-Helfer)."""
        if not self._last_suggestions:
            if not self._generate():
                return False
        return self._apply_suggestion(0)

    def _handle_suggestion_double_click(self, index):
        """Doppelklick übernimmt – außer auf Score, dort erklärt er nur."""
        if index.column() == 4:
            self._maybe_show_why(index)
            return
        self._apply_suggestion(index.row())

    def _maybe_show_why(self, index):
        """Zeigt Why-Score-Dialog beim Klick auf Score-Spalte (Index 4)."""
        if index.column() != 4:
            return
        row = index.row()
        item = self.sug_table.item(row, 4)
        if not item:
            return
        data = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(data, dict):
            return
        dlg = WhyScoreDialog(data, self)
        dlg.exec()

    def _generate(self):
        n = self.slots_spin.value()
        suggestions = self._engine.get_suggestions(
            n,
            paper_id=self._selected_paper_id,
            theme=self._selected_theme,
            avoid_pairs=self._avoid_pairs,
        )
        self._last_suggestions = suggestions  # Cache für Override-Dialog
        # Reroll-Gedächtnis fortschreiben: die jetzt gezeigten Paare werden
        # beim nächsten Klick gemieden (Engine fällt pro Füller automatisch
        # auf den vollen Pool zurück, wenn nichts Neues mehr übrig ist).
        self._avoid_pairs.update((s["pen_id"], s["ink_id"]) for s in suggestions)

        if not suggestions:
            # Diagnose: warum gibt es keine Vorschläge?
            from database.db import get_session as _gs
            from database.models import Pen as _Pen, Ink as _Ink
            _s = _gs()
            try:
                pen_count = _s.query(_Pen).filter_by(is_active=True).count()
                ink_count = _s.query(_Ink).filter_by(is_empty=False, is_archived=False).count()
            finally:
                _s.close()
            if pen_count == 0:
                hint = translate_source_text("Keine aktiven Füller vorhanden. Bitte zuerst Füller anlegen (Füllerverwaltung → + Füller).")
            elif ink_count == 0:
                hint = translate_source_text("Keine Tinten verfügbar. Bitte zuerst Tinten anlegen (Tintenverwaltung → + Tinte).")
            else:
                hint = translate_source_text("Keine direkten Befüllvorschläge. Prüfe unten, welche befüllten Füller geleert werden können.")
            self.sug_info.setText(hint)
            self.sug_table.hide()
            self._refresh_cleaning()
            return False

        # Feder-Hinweis wenn Vorschläge Füller ohne Nib enthalten
        from database.db import get_session as _gs2
        from database.models import Pen as _Pen2
        _s2 = _gs2()
        try:
            no_nib_count = sum(
                1 for sg in suggestions
                if not getattr(_s2.get(_Pen2, sg.get("pen_id", 0)), "nib_id", None)
            )
        finally:
            _s2.close()
        nib_hint = (t('ui.rotation_widget.no_nib_hint', count=no_nib_count) if no_nib_count else "")
        summary = t('ui.rotation_widget.suggestion_summary', count=len(suggestions), nib_hint=nib_hint)
        _pct = next((s.get("random_percent") for s in suggestions if s.get("random_mode")), None)
        if _pct:
            summary = f"🎲 {t('rotation.random_mode_active', pct=_pct)} · {summary}"
        self.sug_info.setText(summary)
        self.sug_table.show()
        self.sug_table.setRowCount(len(suggestions))

        for row, s in enumerate(suggestions):
            color_item = QTableWidgetItem("")
            color_item.setBackground(QColor(s["color_hex"]))
            color_item.setData(Qt.ItemDataRole.UserRole, (s["pen_id"], s["ink_id"]))
            # Score-Spalte: komplettes Dict als UserRole für Why-Dialog
            score_val = int(s.get("score", 0))
            score_item = QTableWidgetItem(str(score_val))
            score_item.setData(Qt.ItemDataRole.UserRole, s)
            score_item.setToolTip(t('ui.rotation_widget.klicke_fur_score_erklarung_b4ccd78a'))
            # Ampel-Färbung für schnelles Scannen (v0.2.79)
            if s.get("has_blocked"):
                score_item.setForeground(QColor("#e74c3c"))
                score_item.setFont(QFont("", -1, QFont.Weight.Bold))
            elif score_val >= 100:
                score_item.setForeground(QColor("#27ae60"))
            elif score_val < 0:
                score_item.setForeground(QColor("#d35400"))
            self.sug_table.setItem(row, 0, color_item)

            for col, key in enumerate(
                ["pen_name", "ink_name", "fill_system", "score", "warnings"], start=1
            ):
                if key == "score":
                    self.sug_table.setItem(row, col, score_item)  # mit Why-Dialog UserRole
                elif key == "warnings":
                    # v0.2.79: Kompakte Anzeige statt Riesen-String.
                    # Regelwarnungen bleiben vollständig sichtbar; von den
                    # Info-Hinweisen erscheinen nur die ersten zwei. Der
                    # komplette Text steckt im Tooltip und im Score-Dialog.
                    rule_parts = [translate_source_text(str(w)) for w in s.get("rule_warnings", [])]
                    hint_parts = [translate_source_text(str(h)) for h in s.get("hints", [])]
                    shown = rule_parts + hint_parts[:2]
                    hidden = len(hint_parts) - 2
                    compact = " | ".join(shown) if shown else t("rotation.hint_no_problems")
                    if hidden > 0:
                        compact += "  " + t("rotation.more_hints", n=hidden)
                    warn_item = QTableWidgetItem(compact)
                    full_lines = rule_parts + hint_parts
                    warn_item.setToolTip("\n".join(full_lines) if full_lines else t("rotation.hint_no_problems"))
                    if rule_parts:
                        warn_item.setForeground(QColor("#d35400"))
                    self.sug_table.setItem(row, col, warn_item)
                else:
                    self.sug_table.setItem(row, col, QTableWidgetItem(str(s[key])))

            # pen_id / ink_id auch in Spalte 1 speichern (für Kontextmenü)
            self.sug_table.item(row, 1).setData(
                Qt.ItemDataRole.UserRole, (s["pen_id"], s["ink_id"])
            )
            btn = QPushButton(t('ui.rotation_widget.ubernehmen_ce5e5cf2'))
            btn.setProperty("class", "success")
            btn.setToolTip(t('ui.rotation_widget.vorschlag_ubernehmen_und_fuller_befullen_0b84c0c8'))
            btn.clicked.connect(lambda _checked=False, r=row: self._apply_suggestion(r))
            self.sug_table.setCellWidget(row, 6, btn)

        return True

    # ------------------------------------------------------------------ #
    # Kontextmenü für Vorschläge                                          #
    # ------------------------------------------------------------------ #
    def _show_suggestion_menu(self, pos):
        row = self.sug_table.rowAt(pos.y())
        if row < 0:
            return
        self.sug_table.selectRow(row)
        ids = self._ids_for_suggestion_row(row)
        if not ids:
            return False

        pen_name = (self.sug_table.item(row, 1) or QTableWidgetItem(t('ui.rotation_widget.fuller_30e41efe'))).text()
        ink_name = (self.sug_table.item(row, 2) or QTableWidgetItem(t('ui.rotation_widget.tinte_0d292b04'))).text()

        menu = QMenu(self)
        apply_action = QAction(t("rotation.apply_action", pen=pen_name, ink=ink_name), self)
        apply_action.triggered.connect(lambda: self._apply_suggestion(row))
        menu.addAction(apply_action)
        menu.addSeparator()
        info_action = QAction(t('ui.rotation_widget.nur_auswahlen_ansehen_8a817600'), self)
        info_action.setEnabled(False)
        menu.addAction(info_action)
        menu.exec(self.sug_table.viewport().mapToGlobal(pos))

    def _ids_for_suggestion_row(self, row: int):
        item = self.sug_table.item(row, 0) or self.sug_table.item(row, 1)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _apply_suggestion(self, row: int):
        ids = self._ids_for_suggestion_row(row)
        if not ids:
            return
        pen_id, ink_id = ids

        # Vorschlag-Dict aus internem Cache holen (enthält rule_warnings)
        suggestion = next(
            (s for s in (self._last_suggestions or [])
             if s.get("pen_id") == pen_id and s.get("ink_id") == ink_id),
            None,
        )
        rule_warnings = (suggestion or {}).get("rule_warnings", []) or []

        override_reason = ""
        if rule_warnings:
            # Bug 7+8: Bei aktiven Regel-Violations Grund erfragen + OverrideLog schreiben
            dlg = OverrideReasonDialog(rule_warnings, self)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return False   # Nutzer hat abgebrochen – harte Regel verhindert stille Übernahme
            override_reason = dlg.reason()

        ok, msg = self._engine.apply_suggestion(pen_id, ink_id, override_reason=override_reason)
        if ok:
            QMessageBox.information(self, t('ui.rotation_widget.rotation_a4ac1446'), msg)
        else:
            QMessageBox.warning(self, t('ui.rotation_widget.rotation_a4ac1446'), msg)
        self.refresh()
        self._generate()
        return bool(ok)

    # ------------------------------------------------------------------ #
    # Leeren-Empfehlungen                                                 #
    # ------------------------------------------------------------------ #
    def _refresh_cleaning(self):
        rows = self._engine.get_empty_candidates_to_clean(self.slots_spin.value())
        self.clean_table.setRowCount(len(rows))

        for r, d in enumerate(rows):
            pen_id = d.get("pen_id")
            self.clean_table.setItem(r, 0, QTableWidgetItem(d.get("pen_name", "")))
            self.clean_table.setItem(r, 1, QTableWidgetItem(d.get("ink_name", "")))
            self.clean_table.setItem(r, 2, QTableWidgetItem(str(int(d.get("clean_score", 0)))))
            self.clean_table.setItem(r, 3, QTableWidgetItem(d.get("reason", "")))

            combo = QComboBox()
            combo.setMinimumWidth(scale_px(300))
            # Platzhalter bleibt vorhanden, aber beste Engine-Empfehlung wird direkt vorausgewählt.
            combo.addItem(t("rotation.select_ink_placeholder"), None)
            current_ink_id = d.get("ink_id")  # aktuell eingefüllte Tinte nicht erneut anbieten
            recommendations = self._engine.get_refill_recommendations_for_pen(
                pen_id,
                exclude_ink_id=current_ink_id,
                paper_id=self._selected_paper_id,
                theme=self._selected_theme,
            )
            for rec in recommendations:
                label = f"{rec.get('ink_name', '')}  · Score {int(rec.get('score', 0))}"
                combo.addItem(label, rec.get("ink_id"))
                idx = combo.count() - 1
                combo.setItemData(idx, " | ".join(translate_source_text(h) for h in (rec.get("hints") or [])[:8]), Qt.ItemDataRole.ToolTipRole)
            if combo.count() > 1:
                combo.setCurrentIndex(1)  # beste Empfehlung vorwählen
            self.clean_table.setCellWidget(r, 4, combo)

            clean_btn = QPushButton(t('ui.rotation_widget.leeren_8e37cb14'))
            clean_btn.setToolTip(t('ui.rotation_widget.aktuelle_tinte_austragen_fuller_als_leer_markier_fb4d51c5'))
            clean_btn.clicked.connect(lambda _checked=False, pid=pen_id: self._clean_pen(pid))
            self.clean_table.setCellWidget(r, 5, clean_btn)

            refill_btn = QPushButton(t('ui.rotation_widget.leeren_befullen_6fc57110'))
            refill_btn.setProperty("class", "success")
            refill_btn.setToolTip(t('ui.rotation_widget.aktuelle_tinte_austragen_und_ausgewahlte_neue_ti_7c64a6cf'))
            refill_btn.clicked.connect(lambda _checked=False, row=r, pid=pen_id: self._clean_and_refill(row, pid))
            self.clean_table.setCellWidget(r, 6, refill_btn)

    def _clean_pen(self, pen_id: int):
        if pen_id is None:
            return
        ok, msg = self._engine.clean_pen(pen_id)
        if ok:
            QMessageBox.information(self, t('ui.rotation_widget.rotation_a4ac1446'), msg)
        else:
            QMessageBox.warning(self, t('ui.rotation_widget.rotation_a4ac1446'), msg)
        self.refresh()

    def _clean_and_refill(self, row: int, pen_id: int):
        if pen_id is None:
            return
        combo = self.clean_table.cellWidget(row, 4)
        if combo is None or combo.currentData() is None:
            QMessageBox.warning(self, t('ui.rotation_widget.rotation_a4ac1446'), t('ui.rotation_widget.bitte_zuerst_eine_neue_tinte_auswahlen_8466e945'))
            return
        ink_id = int(combo.currentData())
        override_reason = ""
        try:
            from database.db import get_session as _gs
            from database.models import Pen as _Pen, Ink as _Ink
            from logic.rule_engine import RuleEngine, LEVEL_ICONS as _LEVEL_ICONS
            _s = _gs()
            try:
                pen = _s.get(_Pen, pen_id)
                ink = _s.get(_Ink, ink_id)
                violations = RuleEngine().check(pen, ink, _s) if pen and ink else []
                rule_warnings = [
                    f"{_LEVEL_ICONS.get(v.warn_level, '⚠')} {v.rule_name}: {v.description}" + (t("rotation.warning_hard_rule_suffix") if v.rule_type == "hard" and v.warn_level != "blocked" else "")
                    for v in violations
                    if v.warn_level in ("blocked", "critical", "warning") or v.rule_type == "hard"
                ]
            finally:
                _s.close()
            if rule_warnings:
                dlg = OverrideReasonDialog(rule_warnings, self)
                if dlg.exec() != QDialog.DialogCode.Accepted:
                    return
                override_reason = dlg.reason()
        except Exception:
            override_reason = ""
        ok, msg = self._engine.clean_and_refill(pen_id, ink_id, override_reason=override_reason)
        if ok:
            QMessageBox.information(self, t('ui.rotation_widget.rotation_a4ac1446'), msg)
        else:
            QMessageBox.warning(self, t('ui.rotation_widget.rotation_a4ac1446'), msg)
        self.refresh()
        self._generate()

    # ------------------------------------------------------------------ #
    # Papier-Kontext (Bug 5)                                              #
    # ------------------------------------------------------------------ #
    def _reload_paper_dropdown(self):
        """Papier-Dropdown neu laden (z.B. nach papers_changed Signal)."""
        from database.db import get_session as _gs
        from database.models import Paper as _Paper
        session = _gs()
        try:
            papers = session.query(_Paper).order_by(_Paper.brand, _Paper.name).all()
        finally:
            session.close()

        self.paper_combo.blockSignals(True)
        current_id = self._selected_paper_id
        self.paper_combo.clear()
        self.paper_combo.addItem(t('ui.rotation_widget.kein_papier_c66737e5'), None)
        for p in papers:
            self.paper_combo.addItem(f"{p.brand} {p.name}", p.id)
        # Vorherige Auswahl wiederherstellen
        for i in range(self.paper_combo.count()):
            if self.paper_combo.itemData(i) == current_id:
                self.paper_combo.setCurrentIndex(i)
                break
        self.paper_combo.blockSignals(False)

    def _on_paper_changed(self, _index: int):
        self._selected_paper_id = self.paper_combo.currentData()
        # Bereits angezeigte Vorschläge hängen vom Papier-Kontext ab.
        # Nach Papierwechsel sofort neu berechnen, sonst sieht der Nutzer alte Scores.
        if self.sug_table.isVisible() or self._last_suggestions:
            self._generate()
        self._refresh_cleaning()

    def _on_theme_changed(self, _index: int):
        self._selected_theme = self.theme_combo.currentData()
        if self.sug_table.isVisible() or self._last_suggestions:
            self._generate()
        self._refresh_cleaning()


# ── Why-Score-Dialog ──────────────────────────────────────────────────────────
class WhyScoreDialog(QDialog):
    """Erklärt warum ein Rotationsvorschlag diesen Score hat."""

    COMPONENTS = [
        ("empty_bonus",     "Füller leer",              "#27ae60",  True),
        ("pen_days_bonus",  "Füller lange leer",        "#2980b9",  True),
        ("ink_days_bonus",  "Tinte lange nicht genutzt", "#16a085", True),
        ("color_delta",     "Farbspektrum",             "#8e44ad",  None),
        ("rule_delta",      "RuleEngine netto",         "#e67e22",  None),
        ("clean_delta",     "Reinigungssicherheit",     "#c0392b",  None),
        ("paper_delta",     "Papier-Kontext",           "#16a085",  None),
        ("role_delta",      "Rollen-Match",             "#9b59b6",  None),
        ("theme_delta",     "Themen-Match",             "#34495e",  None),
        ("duplicate_delta", "Tinte bereits aktiv",      "#c0392b",  None),
        ("diversity_bonus", "Farb-Diversität Set",      "#27ae60",  True),
        ("family_penalty",  "Farbfamilie im Set doppelt", "#c0392b", None),
        ("popularity",      "Zusätzliche Beliebtheit",  "#27ae60",  True),
        ("fixed_bonus",     "Zusätzliche feste Paarung", "#27ae60", True),
        ("must_bonus",      "Zusätzlicher Pflicht-Bonus", "#27ae60", True),
    ]

    def __init__(self, suggestion: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("rotation.score_title", pen=suggestion.get("pen_name", "")))
        self.setMinimumWidth(scale_px(480))
        root = QVBoxLayout(self)
        root.setSpacing(10)

        pen  = suggestion.get("pen_name", "—")
        ink  = suggestion.get("ink_name", "—")
        score = suggestion.get("score", 0)

        root.addWidget(QLabel(t('ui.rotation_widget.why_pen_html', pen=pen)))
        root.addWidget(QLabel(t('ui.rotation_widget.why_ink_html', ink=ink)))
        root.addWidget(QLabel(f"<b>{translate_source_text("Gesamt-Score")}: {score}</b>"))

        # Aufschlüsselung
        root.addWidget(QLabel(t('ui.rotation_widget.text_768089c5')))
        hints = suggestion.get("hints", [])

        # Score-Balken – normiert auf 0-100 für ProgressBar, echter Wert als Label
        for comp_key, comp_label, color, _positive in self.COMPONENTS:
            val = suggestion.get(comp_key, 0)
            if val == 0:
                continue
            row = QHBoxLayout()
            lbl = QLabel(f"{translate_source_text(comp_label)}:")
            lbl.setFixedWidth(180)
            row.addWidget(lbl)
            bar = QProgressBar()
            bar.setRange(0, 100)
            # Auf 0-100 normieren: max. erwarteter Absolutwert ist 150
            normalized = min(100, int(abs(val) / 1.5))
            bar.setValue(normalized)
            sign = "+" if val > 0 else "−"
            bar.setFormat(f"{sign}{abs(val)}")
            bar.setStyleSheet(
                f"QProgressBar::chunk {{ background:{color}; }}"
                " QProgressBar { text-align:center; border-radius:4px; }"
            )
            row.addWidget(bar)
            root.addLayout(row)

        # Hinweise aus der Engine
        if hints:
            root.addWidget(QLabel(t('ui.rotation_widget.hinweise_d2cb3675')))
            for h in hints:
                lbl = QLabel(f"  • {translate_source_text(h)}")
                lbl.setStyleSheet("color:#555; font-size:12px;")
                lbl.setWordWrap(True)
                root.addWidget(lbl)

        # Regelwarnungen: bewusst eigene Liste verwenden.
        # suggestion["warnings"] ist der zusammengefasste Tabellen-Text.
        rule_warnings = suggestion.get("rule_warnings", []) or []
        if rule_warnings:
            root.addWidget(QLabel(t('ui.rotation_widget.regeln_f8c472e3')))
            for w in rule_warnings:
                lbl = QLabel(f"  ⚠  {translate_source_text(w)}")
                lbl.setStyleSheet("color:#c0392b; font-size:12px;")
                lbl.setWordWrap(True)
                root.addWidget(lbl)

        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(self.reject)
        root.addWidget(bb)


# ── Override-Reason-Dialog ─────────────────────────────────────────────────────
class OverrideReasonDialog(QDialog):
    """Fordert den Nutzer auf, einen Override-Grund einzugeben.

    Erscheint wenn ein Rotationsvorschlag aktive Regelwarnungen hat und
    trotzdem übernommen werden soll. Der Grund wird im OverrideLog gespeichert.
    """

    def __init__(self, rule_warnings: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t('ui.rotation_widget.regeluberschreibung_bestatigen_798648d8'))
        self.setMinimumWidth(scale_px(500))
        root = QVBoxLayout(self)
        root.setSpacing(12)

        warn_lbl = QLabel(t('ui.rotation_widget.diese_kombination_verletzt_aktive_regeln_a67b94ee'))
        root.addWidget(warn_lbl)

        for w in rule_warnings:
            lbl = QLabel(f"  ⚠  {translate_source_text(w)}")
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color:#c0392b; font-size:12px; padding:2px 8px;")
            root.addWidget(lbl)

        note = QLabel(
            t('ui.rotation_widget.du_kannst_die_kombination_trotzdem_ubernehmen_bi_ebf883d4')
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#555; font-size:12px; margin-top:6px;")
        root.addWidget(note)

        from PySide6.QtWidgets import QLineEdit
        self._reason_edit = QLineEdit()
        self._reason_edit.setPlaceholderText(t('ui.rotation_widget.grund_z_b_bewusste_entscheidung_testbefullung_214a9e2c'))
        root.addWidget(self._reason_edit)

        bb = QDialogButtonBox()
        confirm_btn = bb.addButton("Override bestätigen", QDialogButtonBox.ButtonRole.AcceptRole)
        confirm_btn.setStyleSheet(
            "background:#e74c3c; color:white; border:none;"
            " padding:7px 16px; border-radius:5px; font-weight:bold;"
        )
        bb.addButton(t("common.cancel"), QDialogButtonBox.ButtonRole.RejectRole)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        root.addWidget(bb)

    def reason(self) -> str:
        return self._reason_edit.text().strip() or t("ui.rotation_widget.no_reason_given")
