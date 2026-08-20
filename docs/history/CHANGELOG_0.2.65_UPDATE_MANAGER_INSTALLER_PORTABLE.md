# Changelog v0.2.65 — Update Manager, Installer, Portable Merge

Datum: 5. Juli 2026

## Ziel

Diese Version führt die besseren Teile aus FPM v0.2.63 und FPM v0.2.64 zusammen und ergänzt einen BudgetManager-ähnlichen Update- und Release-Weg.

## Übernommen aus v0.2.64

- Wishlist → BudgetManager-Bridge bleibt erhalten.
- BudgetManager-Sparziele bleiben lesbar und im Dashboard nutzbar.
- Outbox-Synchronisierung nach Kauf-/Ausgabenaktionen bleibt erhalten.
- Import-/Export-Einstellungen für die BudgetManager-Bridge bleiben erhalten.

## Wiederhergestellt aus v0.2.63

- Windows-Packaging-Struktur mit PyInstaller-Spec, Build-Skript und GitHub-Workflow.
- Datenbank-Härtung mit Schema-Version und Migrationen.
- Schreibprobenvergleich mit robusterer Gewinnerlogik.
- Tinten-Restmengenlogik inklusive Verbrauchsbuchung und Nachkaufempfehlung.
- Feder-Tausch-Historie und dazugehörige Legacy-Migrationen.
- Härtung der Enthusiast-Lab-Logik, damit optionale Features nicht zum Pflichtworkflow werden.

## Neu in v0.2.65

- Neuer Updatemanager nach BudgetManager-Prinzip:
  - Manifest-basiert über `latest.json`.
  - SHA256-Pflichtprüfung vor Anwendung eines Updates.
  - Installer-Installationen bevorzugen `windows_installer`.
  - Portable Installationen bevorzugen portable ZIPs.
  - Platzhalter-Git-Link ist vorbereitet und muss nach Erstellung des Repos ersetzt werden.
- Neuer Update-Dialog in den Einstellungen.
- CLI-Hooks:
  - `--check-update`
  - `--apply-update`
- Neues Installer-Skript `installer/FountainPenManager_Setup.iss`:
  - Datenordner auswählbar.
  - Portable/Installer-Datenlogik getrennt.
  - Erstkonfiguration wird als `config.json` vorbereitet.
  - `installation.json` markiert Installer-Installationen.
- Verbesserte portable Version:
  - Windows-Starter `start-windows.cmd` setzt `FPM_DATA_DIR` auf `./data`.
  - Linux-Starter `start-linux.sh` setzt `FPM_DATA_DIR` auf `./data`.
  - Daten, Backups und Einstellungen bleiben im Portable-Ordner.
- Neue Release-Asset-Builder:
  - `tools/build_windows.py`
  - `tools/build_release_assets.py`
- Versionssynchronisation:
  - `tools/sync_version.py`
  - `version.json`
  - `VERSION_INFO.txt`
  - `latest.json.template`
  - `docs/latest.json.template`

## Behobene Logikfehler

- v0.2.64 hatte gegenüber v0.2.63 Regressionen bei DB-Migrationen. Diese sind behoben.
- v0.2.64 hatte Teile der Tinten-Restmengen- und Nachkauf-Logik verloren. Diese sind wiederhergestellt.
- v0.2.64 hatte Schreibproben-Vergleichslogik vereinfacht. Die robustere Auswahl aus v0.2.63 ist wieder aktiv.
- v0.2.64 hatte Packaging-/Installer-Dateien nicht vollständig übernommen. Diese sind jetzt integriert und erweitert.
- Portable Datenpfade waren nicht klar von Installer-Datenpfaden getrennt. Jetzt gilt:
  - Portable: `FPM_DATA_DIR` / `./data`
  - Installer: `installation.json` → gewählter Datenordner
  - Fallback: `~/.fpm_data`

## Validierung

- `python -m compileall -q .` erfolgreich.
- `python -m pytest -q` erfolgreich: 86 Tests bestanden.
- I18N-Audits erfolgreich:
  - 1869 Keys × 3 Sprachen vollständig.
  - Keine erkannten untranslated/leakage/ternary-Literal-Probleme.
  - Keine direkten sichtbaren deutschen Qt-Textaufrufe im Audit.
- `python tools/sync_version.py --check` erfolgreich.

## Noch offen nach Git-Erstellung

Der Platzhalter `sloogy/FPM` muss durch den echten GitHub-Pfad ersetzt werden in:

- `updater/common.py`
- `ui/update_dialog.py`
- `installer/FountainPenManager_Setup.iss`
- `latest.json.template`
- `docs/latest.json.template`

Der GitHub-Workflow erzeugt bei echtem Repository automatisch Release-URLs auf Basis von `${{ github.repository }}`.
