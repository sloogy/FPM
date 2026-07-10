# Changelog 0.2.71 – Release-Readiness UI/I18N Hardening

**Datum:** 6. Juli 2026  
**Basis:** v0.2.70 KILLCRITIC DAU Usability Merge  
**Scope:** Umsetzung aller Auditpunkte außer Updater-/GitHub-OWNER-Platzhalter.

## Geändert

- Version auf `0.2.71` angehoben:
  - `app_info.py`
  - `version.json`
  - `VERSION_INFO.txt`
  - Installer-Metadaten
  - `latest.json.template`
  - `docs/latest.json.template`
  - i18n-App-Version
  - Schema-Version
- README vollständig auf v0.2.71 aktualisiert.
- Windows-Release-Dokumente DE/EN/FR von v0.2.67 auf v0.2.71 aktualisiert.
- Navigation DAU-freundlich gruppiert:
  - Start
  - Sammlung
  - Tägliche Nutzung
  - Auswertung
  - System
- Shortcuts für alle 14 Module ergänzt:
  - `Ctrl+1` bis `Ctrl+9`
  - `Alt+1` bis `Alt+5`
- Sidebar-Gruppenlabels visuell hervorgehoben.

## Runtime-I18N gehärtet

- Deutsche Laufzeittexte aus folgenden Logikpfaden in Übersetzungsschlüssel verschoben:
  - `logic/rotation_engine.py`
  - `logic/rule_engine.py`
  - `logic/auto_mode_service.py`
- Full-Auto-Aktionen und Regelgruppen lokalisiert.
- Regel-Erklärungen werden nun über `rule_engine.*`-Keys erzeugt.
- Rotationsmeldungen, Reinigungsgründe, Füllsystemlabels und Notizen werden über i18n erzeugt.

## GUI-Smoke-Test ergänzt

- Manueller GUI-Smoke-Test in drei Sprachen ergänzt:
  - `docs/GUI_SMOKE_TEST_DE.md`
  - `docs/GUI_SMOKE_TEST_EN.md`
  - `docs/GUI_SMOKE_TEST_FR.md`
- Automatischer Kurztest ergänzt:
  - `tools/gui_smoke_test.py`
- Der automatische Test prüft bei vorhandener PySide6-Umgebung:
  - App-Imports
  - DB-Initialisierung mit temporärem Datenordner
  - MainWindow-Erzeugung
  - Lazy-Navigation durch alle 14 Module
  - Grundlegende DE/EN/FR-i18n-Schlüssel

## Tests

- Neue statische Release-Readiness-Tests ergänzt:
  - aktuelle README/Windows-Doku
  - gruppierte Navigation
  - zentrale Runtime-I18N-Schlüssel
  - GUI-Smoke-Dokumentation und Smoke-Script

## Bewusst nicht umgesetzt

- Updater-/GitHub-OWNER-Platzhalter wurden nicht ersetzt und nicht deaktiviert, weil dies explizit ausgenommen wurde.
