# Release Report – FountainPen Manager v0.2.77

**Basis:** v0.2.76 (Simple Mode / Expert Area) · **Build:** quick-actions-mode-logic-hardening · **Datum:** 7. Juli 2026

## Kurzurteil

**Freigabe empfohlen als Source/Portable-RC.** Die v0.2.76-Basis ist die bisher
rundeste Version des Projekts: Der neue Simple/Expert-Modus ist sauber gebaut
(zentrale `logic/app_mode.py`, `fallback_page`-Absicherung in `_navigate`,
sauberer Sidebar-Neuaufbau). Die Tiefenprüfung fand **einen dringenden
Funktionsfehler** (stumme Befüllen-/Reinigen-Schnellaktionen) und **einen
Release-Doku-Pin** – beide behoben. Drei Anfangsverdachte stellten sich bei
Verifikation als unbegründet heraus und wurden **nicht** „gefixt".

## 200er-Prüfmatrix – 20 Themen × 10 Prüfpunkte

| # | Thema | Ergebnis |
|---|---|---|
| 1 | Start/Imports/Kompilierung | OK, ganzer Baum kompiliert |
| 2 | Versionierung/Sync/Pins | Gefixt: 0275-Pin-Test übersehen → nachgezogen; sync 0.2.77 grün |
| 3 | app_mode-Logik (get/set/normalize) | OK; `AppSettings.set` committet selbst (Verdacht „kein Commit" **widerlegt**) |
| 4 | fallback_page/page_visible | OK, jetzt **funktional** getestet (alle 14 Seiten × beide Modi) |
| 5 | Sidebar-Neuaufbau | OK: `_clear_layout()`+`_buttons.clear()` → keine Duplikate (Verdacht widerlegt) |
| 6 | Moduswechsel-Konsistenz | OK: `modeChanged` → MainWindow leitet von versteckten Seiten um |
| 7 | Shortcuts im Simple Mode | OK: `_navigate` wendet `fallback_page` selbst an (Ctrl+7 → Dashboard) |
| 8 | Dashboard-Schnellaktionen | **Gefixt:** fill/clean ohne Selektion = stumm → Ein-Füller-Autowahl + Hinweis |
| 9 | Toolbar-Schnellaktionen | Selber Fix greift (gemeinsamer `_run_page_action`-Pfad) |
| 10 | Settings-Modus-Combo | OK funktional; Stil-Smell: ruft `sidebar._setup_ui()` privat (Refactoring-Notiz) |
| 11 | Zwei Umschaltwege synchron | OK: beide persistieren via `set_app_mode`/`AppSettings`, Sidebar liest neu |
| 12 | Indexstabilität Navigation | OK: Stack unverändert, Buttons tragen feste `page` |
| 13 | i18n neue Keys/Verdrahtung | OK: alle 5 Audits grün, 1974 × 3, 0 Waisen, Platzhalter-Parität 0 Diffs |
| 14 | Session-Disziplin Neu-Code | OK: app_mode/get/set mit try/finally close |
| 15 | event_bus headless | OK (live bewiesen: Import + connect/emit ohne PySide6) |
| 16 | README/Release-Doku | **Gefixt:** Links auf 0.2.77-Dokumente, Dateien angelegt; 0275-Guard grün |
| 17 | Tests/Regression | 141 grün (+6 funktionale Modus-/Fix-Guards); nur SQLAlchemy-Migrationstest sandbox-blockiert |
| 18 | Updater/GitHub-Pfade | OK: `sloogy/FPM` konsistent, `is_newer` semantisch (packaging) |
| 19 | Wishlist-Tour-CTA im Simple | Randnotiz: Dialog öffnet korrekt, Seite dahinter fällt aufs Dashboard zurück – funktional ok |
| 20 | Ehrlichkeit der Prüfwerkzeuge | 3 Falsch-Verdachte verifiziert & verworfen; eigener AST-Test um `AnnAssign` korrigiert |

## Der Kernfix im Detail

**Problem:** Die Simple-Mode-Kernaktionen „Füller befüllen" und „Reinigung
eintragen" (Dashboard-Panel **und** Toolbar) riefen `_load_ink`/`_mark_cleaned`
auf, die ohne Tabellen-Selektion **kommentarlos** returnen. Genau die
Zielgruppe des Modus (Einsteiger, frisch geöffnete Seite, keine Selektion)
erlebte tote Buttons – der Kernnutzen des Features lief ins Leere.

**Fix:** `PenWidget._quick_pen_id()` – Selektion > Ein-Füller-Autowahl >
freundlicher i18n-Hinweis. Kein Verhaltensbruch für Bestandsnutzung; der
Ein-Füller-Fall (typischer Einsteiger) funktioniert jetzt in einem Klick.

## Verifizierte Nicht-Fehler (bewusst nicht „gefixt")

1. `set_app_mode` ohne explizites Commit → `AppSettings.set` committet in
   dieser Codebasis selbst; Persistenz live nachvollzogen.
2. Sidebar-Doppelaufbau durch `settings._save` → `_setup_ui` leert Layout und
   Button-Map zuvor; nur Stil-Smell (private API von außen), als
   Refactoring-Kandidat notiert (`rebuild()`-Fassade).
3. Scheinbares Code-Duplikat in `_global_search_changed` → Artefakt meiner
   überlappenden Lese-Fenster, Quelle ist sauber.

## Validierung

```text
python -m compileall -q .            → OK
Testsuite (headless Harness)         → 141 passed
tools/sync_version.py --check        → Alle Versionsdateien synchron: 0.2.77
alle fünf i18n-Audits                → OK (1974 Keys × 3 Sprachen)
Key-/Platzhalter-Parität (eigene)    → 0 Waisen, 0 Platzhalter-Diffs
logic.app_mode funktional            → 28 Einzel-Asserts über beide Modi grün
event_bus ohne PySide6               → Import/connect/emit live verifiziert
```

## Offene Pflichtschritte vor dem finalen Windows-Release

1. **GUI-Smoke-Test** auf echter PySide6-/Windows-Umgebung
   (`docs/GUI_SMOKE_TEST_*.md`) – neu dazu: (a) Dashboard-Buttons „Befüllen"/
   „Reinigen" einmal **ohne** Selektion mit 1 Füller (Autowahl) und mit
   mehreren Füllern (Hinweis-Dialog) prüfen, (b) Moduswechsel von einer
   Expertenseite aus (Rücksprung aufs Dashboard), (c) Settings-Combo und
   Sidebar-Button wechselseitig.
2. Echte Artefakte + SHA256 in `latest.json` beim GitHub-Release.
