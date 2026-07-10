# FPM v0.2.50 – P1 i18n-Fixreport

**Basis:** FPM v0.2.50 statistics_ui_rc  
**Patch:** P1 i18n/helper wiring  
**Datum:** 2026-06-06

## Ergebnis

P1 wurde umgesetzt. Die zuvor gefundenen sichtbaren Direkttexte in Dashboard, Ausgaben-Summary und Tinten-Detail wurden auf echte i18n-Keys umgestellt. Zusätzlich wurden weitere sichtbare Helper-Texte in Help, Pen-Detail und Settings explizit über `t(...)` verdrahtet, damit der erweiterte Audit nicht grün meldet, obwohl Custom-Helper noch Literale anzeigen.

## Geänderte Bereiche

### Dashboard

Umgestellt auf i18n-Keys:

- Füller aktiv
- Mit Tinte
- Tinten
- Sammlungswert
- Ink Safety Timer
- Service/Sperren
- Archiviert

Datei:

- `ui/dashboard_widget.py`

### Ausgaben-Tracker

Die Summary-Karten verwenden nun i18n-Keys:

- Gesamt
- Füller
- Tinten
- Federn
- Papier
- Service
- Rest

Datei:

- `ui/expenses_widget.py`

### Tinten-Detailansicht

Umgestellt auf i18n-Keys:

- Feathering
- Shading
- Einsätze gesamt

Datei:

- `ui/ink_widget.py`

### Weitere sichtbare Helper-Texte

Zusätzlich explizit verdrahtet:

- Help-Karten
- Pen-Detailzeilen
- Settings-Seiten, Karten, Notes und Buttons

Dateien:

- `ui/help_widget.py`
- `ui/pen_widget.py`
- `ui/settings_widget.py`

### i18n-Dateien

Neue Keys wurden ergänzt in:

- `i18n/de.json`
- `i18n/en.json`
- `i18n/fr.json`

Die `legacy_exact.*`-Keys wurden **nicht gelöscht**.

### Audit-Erweiterung

Der i18n-Key-Wiring-Audit und Runtime-Audit erkennen nun zusätzliche sichtbare Custom-Helper:

- `_card`
- `_summary_card`
- `row`
- `_note`
- `_styled_button`
- `_new_page`
- `_v_card`
- `_form_card`

Dateien:

- `tools/i18n_key_wiring_audit.py`
- `tools/i18n_runtime_audit.py`

## Validierung

Ausgeführt:

```text
python -m compileall -q .
python tools/i18n_audit.py
python tools/i18n_quality_audit.py
python tools/i18n_key_wiring_audit.py
python tools/i18n_runtime_audit.py
pytest -q
```

Ergebnis:

```text
compile_ok
i18n audit: OK (1473 Keys × 3 Sprachen)
i18n quality audit: OK (0 untranslated, 0 leakage, 0 ternary literals)
i18n key wiring audit: OK (0 direct visible German literals in Qt text calls)
i18n runtime audit: OK (0 likely visible German UI strings covered for EN/FR)
43 passed
```

Zusätzlich:

```text
python dev_check.py
```

Ergebnis:

```text
Syntaxcheck: OK
Lokale Importnamen: OK
```

Hinweis: Während der Prüfung erzeugte `__pycache__`-Ordner wurden vor dem Verpacken entfernt.

## Nicht geprüft

Nicht geprüft werden konnte in dieser Umgebung:

- echter GUI-Start mit PySide6
- echte DB-Laufzeit mit SQLAlchemy
- Migration alter Datenbanken
- visueller Sprachwechsel Deutsch/Englisch/Französisch

Diese Punkte bleiben vor einer finalen Release-Freigabe als manueller RC-Smoke-Test offen.

## Release-Empfehlung

Dieser Patch beseitigt die P1-i18n-Abweichungen aus dem Review. Für einen finalen Release sollten danach noch GUI-Runtime und DB-Migration manuell getestet werden.
