# FountainPen Manager v1.2.3

FountainPen Manager ist eine lokale Desktop-App zur Verwaltung von Füllern, Tinten, Federn, Papier, Schreibproben, Rotation, Pflege, Ausgaben, Wishlist und Sammlerwert.

## Release-Fokus v1.0.0

- Zentraler SSRF-Schutz für Bildimport, Online-Referenzsuche und Updater; private, lokale und link-lokale Netze sowie unsichere Redirects werden blockiert.
- Aktive Downloads lassen sich tatsächlich abbrechen; Größenlimits und atomare Update-Downloads verhindern unvollständige Dateien.
- SQLite-Sicherheitsbackups werden vor Migrationen konsistent, integritätsgeprüft und atomar erzeugt.
- Rotierende Produktionslogs, globale Crash-Hooks und ein datenschutzarmes Diagnosepaket verbessern den Support.
- Windows-/Linux-Releases verwenden getrennte Hash-Locks und vollständige Gates. Windows-App und Installer werden bis zur späteren gemeinsamen Key-Einrichtung ausdrücklich als unsigned veröffentlicht.
- LifePlanner-/LiveManager-Module entstehen im selben gegateten Publishjob wie die Standalone-Assets. RC- und stabile `.lpmodule` bleiben im vorgesehenen `--allow-unsigned`-Modus und verlangen bei lokaler Installation eine ausdrückliche Vertrauensbestätigung.
- 424 Tests, fünf i18n-Audits, GUI-Smoke sowie 139.000 KILLCRITIC-Checks sind in der hash-gelockten Linux-Release-Umgebung grün; auch das gebaute PyInstaller-Bundle initialisiert erfolgreich.

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

- Erfolgreicher Testtag: `v0.3.05-rc.2` mit Windows-/Linux-Testartefakten und beiden `.lpmodule`-Paketen
- Finaler unsigned Vollrelease: `v0.3.05`; Keys werden bewusst erst später gemeinsam eingerichtet
- Status dieses Pakets: lokal vollständig validierter Enterprise-Release-Candidate
- Beide Plattform-Locks sind erzeugt und installationsgeprüft; die GitHub-Matrix, Checksummen, Warnhinweise und Host-Testinstallation bleiben vor der Veröffentlichung verbindlich.
- Ablauf: [Enterprise-Release-Runbook](docs/ENTERPRISE_RELEASE_RUNBOOK_DE.md)
- Offizieller Releasepfad: `https://github.com/sloogy/FPM/releases`
- Daten und Medien liegen außerhalb des Programmordners beziehungsweise im portablen `data/`-Ordner.
