# Release Report – FountainPen Manager v0.2.66 KILLCRITIC

## Ergebnis
**Status: Releasefähig als Source-/Portable-Kandidat.**

Die Version v0.2.65 wurde kritisch geprüft, gehärtet und als v0.2.66 neu paketiert. Die wichtigsten Release-Risiken lagen nicht in Syntax oder i18n, sondern in Rotationsentscheidungen und Sammler-Workflow-Tiefe. Diese Punkte wurden behoben beziehungsweise erweitert.

## Prüfmatrix: 100er KILLCRITIC-Loop, 10 pro Thema

| Thema | Prüfschwerpunkt | Ergebnis |
|---|---|---|
| 1. Start/Grundstruktur | Imports, Syntax, Modultrennung, Startpfade, Portabilität, App-Metadaten | OK |
| 2. Datenbank/Migration | Schema-Version, AppSettings, Default-Regeln, rückwärtskompatible Settings | OK, Schema 0.2.66 |
| 3. Rotation | aktive Füller, aktive Tinten, fixe Zuordnungen, Risiko-Scoring, EDC-Logik | Gehärtet |
| 4. Tintenlogik | Restmenge, leere Flaschen, Befüllvolumen, Clamp-Logik, zentrale Helfer | Gehärtet |
| 5. Füller-Sammlerlogik | Maße, Modellpflege, Sammlerfelder, manuelle Kontrolle, Nicht-Überschreiben | Erweitert |
| 6. Enthusiasten-Usability | schneller Lookup, optionale Funktionen, Sammler-Workflow, vorhandene Daten schützen | Erweitert |
| 7. Mehrsprachigkeit | DE/EN/FR Keys, harte sichtbare Texte, Runtime-Wiring, Qualität | OK, 1877 Keys × 3 |
| 8. Tests/Regression | Unit-Tests, statische Guards, PySide6-arme CI, Verbrauchs-/Dimensionslogik | 93 passed |
| 9. Installer/Versionierung | version.json, VERSION_INFO, Installer, latest templates, Docs | OK, 0.2.66 |
| 10. Release-Hygiene | Pycache, Cache-Dateien, Paketstruktur, Report/Changelog | Bereinigt |

## Behobene Punkte

### 1. Aktive Tinten wurden zu leicht erneut vorgeschlagen
Vorher konnte eine Tinte, die bereits in einem aktiven Füller verwendet wird, trotz Malus erneut vorgeschlagen werden. Das ist für Rotation, Farbspektrum und Safety Timer ungünstig.

**Fix:**
- Exakte aktive Tinte wird standardmäßig übersprungen.
- Fixe Füller-Tinten-Zuordnung bleibt erlaubt.
- Override über Setting `rotation_allow_active_ink_duplicates` vorbereitet.

### 2. Ink-Verbrauch war nicht zentral genug
Der Verbrauch beim Befüllen wurde in der Rotation direkt berechnet.

**Fix:**
- `RotationEngine.fill_pen()` verwendet jetzt `apply_ink_consumption()`.
- Negative Restmengen werden verhindert.
- Leere Flaschen werden sauber markiert.

### 3. Füller-Dimensionen waren rein manuell
Füllermaße waren speicherbar, aber der Workflow für Recherche/Übernahme fehlte.

**Fix/Erweiterung:**
- Neuer Service `pen_dimensions_service.py`.
- Lokaler JSON-Cache für Modellmaße.
- Browsergestützte Suche, wenn kein Cachetreffer vorhanden ist.
- UI-Button im Füller-Dialog.
- Werte werden nur in leere Felder eingetragen.

### 4. CI-freundliche Regression
Ein echter Engine-Import kann in PySide6-freien Umgebungen fehlschlagen, weil die Engine über EventBus Qt berührt.

**Fix:**
- Regression für die kritische Rotationslogik als statischer Source-Test ergänzt.
- Dadurch bleibt die Prüfung CI-fähig ohne GUI-Runtime.

## Neu/geändert – Dateien

- `logic/pen_dimensions_service.py`
- `logic/rotation_engine.py`
- `database/db.py`
- `ui/pen_widget.py`
- `i18n/de.json`
- `i18n/en.json`
- `i18n/fr.json`
- `tests/test_pen_dimensions_service.py`
- `tests/test_rotation_helpers.py`
- `app_info.py`
- `version.json`
- `VERSION_INFO.txt`
- `latest.json.template`
- `docs/latest.json.template`
- `installer/FountainPenManager_Setup.iss`
- `docs/WINDOWS_RELEASE_DE.md`
- `docs/WINDOWS_RELEASE_EN.md`
- `docs/WINDOWS_RELEASE_FR.md`

## Validierung

```text
python -m pytest -q
93 passed

python tools/sync_version.py --check
Alle Versionsdateien synchron: 0.2.66

python tools/i18n_audit.py
i18n audit: OK (1877 Keys × 3 Sprachen)

python tools/i18n_quality_audit.py
i18n quality audit: OK

python tools/i18n_runtime_audit.py
i18n runtime audit: OK

python tools/i18n_key_wiring_audit.py
i18n key wiring audit: OK

python tools/i18n_visible_text_audit.py
i18n visible text audit: OK

python -m compileall -q .
OK

python dev_check.py
Syntaxcheck OK, lokale Importnamen OK
```

## Ehrliche Einschränkungen

- Kein echter Windows-Installer-Build in dieser Sandbox ausgeführt.
- Kein echter GUI-Smoke-Test mit PySide6-Desktopfenster ausgeführt.
- Die Dimensionsabfrage ist absichtlich kein Scraper. Sie nutzt lokalen Cache und öffnet eine Recherche im Browser, weil fremde Shop-/Wiki-Seiten nicht stabil genug für eine harte automatische Datenübernahme sind.

## Release-Urteil

**Freigabe empfohlen für v0.2.66 Source/Portable RC.**

Für ein endgültiges öffentliches Windows-Release sollten zusätzlich noch ein echter Windows-Build, ein Installer-Test und ein manueller GUI-Smoke-Test auf Windows durchgeführt werden.
