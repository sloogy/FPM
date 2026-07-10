# v0.2.44 – Keyed i18n Loop

Ziel: sichtbare deutsche UI-Literale nicht mehr nur per Runtime-Brücke übersetzen,
sondern schrittweise durch stabile `t("...")`-Keys ersetzen — ohne den teuren
globalen `QWidget.show`-Monkeypatch aus v0.2.43.

## Änderungen

- 781 direkte sichtbare Qt-String-Literale automatisiert auf `t("ui.<modul>...")` umgestellt.
- Formatierte Dialog-/Tooltip-/Statusmeldungen mit Platzhaltern manuell auf benannte Keys umgestellt.
- Übersetzungsdateien DE/EN/FR auf 987 identische Keys erweitert.
- `QWidget.show` wird **nicht mehr monkey-gepatcht**.
- `MainWindow` läuft nicht mehr bei jedem Navigations-/Refresh-Vorgang rekursiv über den Widgetbaum.
- Runtime-Fallback ist auf kleine transiente Objekte begrenzt: Dialoge, Menüs, QMessageBox/QFileDialog/QInputDialog.
- ComboBox-Übersetzung speichert keine komplette Itemliste mehr. Pro Item wird eine Quelle in einer separaten UserRole abgelegt und bei Repopulation invalidiert.
- Neues Audit `tools/i18n_key_wiring_audit.py` prüft:
  - keine direkt sichtbaren deutschen Qt-Literale in typischen Text-Calls,
  - kein globaler `QWidget.show`-Hook,
  - kein alter `_fpm_i18n_combo_items`-Cache,
  - keine rekursiven i18n-Scans im MainWindow-Refresh.

## Geprüft

```bash
python3 tools/i18n_audit.py
python3 tools/i18n_runtime_audit.py
python3 tools/i18n_key_wiring_audit.py
python3 -m compileall -q .
```

Ergebnis:

```text
i18n audit: OK (987 Keys × 3 Sprachen)
i18n runtime audit: OK (0 likely visible German UI strings covered for EN/FR)
i18n key wiring audit: OK (0 direct visible German literals in Qt text calls)
compileall: OK
```

## Hinweis

Nicht-sichtbare Konstanten, interne Enum-Werte, Kommentare, Docstrings und
Stylesheet-Fragmente bleiben bewusst unverändert. Sichtbare dynamische Werte aus
älteren Daten-/Label-Maps werden zusätzlich durch den kleinen Dialog-/Menü-Fallback
abgesichert, aber nicht mehr bei jedem `show()` global durch den gesamten UI-Baum
gejagt.
