# FountainPen Manager v0.3.05

FountainPen Manager ist eine lokale Desktop-App zur Verwaltung von Füllern, Tinten, Federn, Papier, Schreibproben, Rotation, Pflege, Ausgaben, Wishlist und Sammlerwert.

## Release-Fokus v0.3.05

- Zentraler SSRF-Schutz für Bildimport, Online-Referenzsuche und Updater; private, lokale und link-lokale Netze sowie unsichere Redirects werden blockiert.
- Aktive Downloads lassen sich tatsächlich abbrechen; Größenlimits und atomare Update-Downloads verhindern unvollständige Dateien.
- SQLite-Sicherheitsbackups werden vor Migrationen konsistent, integritätsgeprüft und atomar erzeugt.
- Rotierende Produktionslogs, globale Crash-Hooks und ein datenschutzarmes Diagnosepaket verbessern den Support.
- Windows-/Linux-Releases verwenden getrennte Hash-Locks, vollständige Gates und verpflichtende Authenticode-Prüfung für Tag-Releases.
- LifePlanner-Module entstehen nur aus bereits gegateten, Ed25519-attestierten Runtime-Artefakten; Modulbau und Standalone-Assets laufen durch denselben Publishjob.
- 418 Tests, fünf i18n-Audits, GUI-Smoke sowie 139.000 KILLCRITIC-Checks sind in der hash-gelockten Linux-Release-Umgebung grün; auch das gebaute PyInstaller-Bundle initialisiert erfolgreich.

## Handbücher

- [Deutsch](docs/BENUTZERHANDBUCH_DE.md)
- [English](docs/USER_MANUAL_EN.md)
- [Français](docs/MANUEL_UTILISATEUR_FR.md)

## Kernbereiche

- Füller-, Tinten-, Feder- und Papierverwaltung
- Regelbasierte Rotation mit Override-System
- Ink Safety Timer und Wartungsüberwachung
- Tinten-Restmengen und Reinigungsprotokolle
- Ausgaben, Sammlerwert und BudgetManager-Brücke
- Schreibproben und Vergleichsansicht
- Optionales Enthusiasten-Lab
- Offlinefähige SQLite-Datenhaltung
- DE/EN/FR-Oberfläche

## Entwicklung und Validierung

```bash
python tools/sync_version.py --check
python tools/check_windows_paths.py
python tools/import_smoke.py
python tools/name_audit.py
python tools/exception_audit.py
python tools/db_access_audit.py
python -m compileall -q .
python -m ruff check . --select E9,F63,F7,F82
python -m bandit -q -r database logic ui updater main.py tools -x tests --severity-level medium
python -m pytest -q --cov=logic --cov=database --cov=updater --cov-fail-under=65
python -m pytest -q tests/test_updater_behavior_0301.py tests/test_updater_enterprise_0304.py \
  --cov=updater.check_update --cov=updater.apply_update --cov=updater.startup_check \
  --cov-fail-under=85
python tools/i18n_audit.py
python tools/i18n_quality_audit.py
python tools/i18n_key_wiring_audit.py
python tools/i18n_runtime_audit.py
python tools/i18n_visible_text_audit.py
QT_QPA_PLATFORM=offscreen python tools/gui_smoke_test.py
```

Offizielle Builds installieren ausschließlich `constraints-linux.lock` bzw. `constraints-windows.lock` mit `--require-hashes --only-binary=:all:`.

## Release

- Nächster Testtag: `v0.3.05-rc.1` für einen klar als unsigned markierten GitHub-Prerelease mit Windows-/Linux-Testartefakten
- Finaler Produktionstag nach erfolgreichem RC-Test und Key-Einrichtung: `v0.3.05`
- Status dieses Pakets: lokal vollständig validierter Enterprise-Release-Candidate
- Beide Plattform-Locks sind erzeugt und installationsgeprüft; vor der öffentlichen Binärfreigabe bleiben die GitHub-Matrix und die realen Authenticode-Signaturen verbindlich.
- Für Release-Module muss zusätzlich `LIFEPLANNER_UPDATE_PRIVATE_KEY_B64` als 32-Byte-Ed25519-Key (Base64) gesetzt sein.
- Ablauf: [Enterprise-Release-Runbook](docs/ENTERPRISE_RELEASE_RUNBOOK_DE.md)
- Offizieller Releasepfad: `https://github.com/sloogy/FPM/releases`
- Daten und Medien liegen außerhalb des Programmordners beziehungsweise im portablen `data/`-Ordner.
