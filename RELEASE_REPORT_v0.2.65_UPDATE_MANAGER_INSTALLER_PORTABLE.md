# Release Report v0.2.65 — Update Manager / Installer / Portable

Datum: 5. Juli 2026
Status: Release Candidate / source release ready

## Ergebnis

FPM v0.2.65 ist die zusammengeführte und gehärtete Version aus:

- `FPM_v0.2.63_WINDOWS_PACKAGING_INSTALLER_RELEASE_READY`
- `FPM_v0.2.64_WISHLIST_BUDGETMANAGER_BRIDGE_HOTFIX_RELEASE_READY`
- BudgetManager v2.2.9 als Referenz für Update-/Installer-/Portable-Architektur

Die Version ist als Quellpaket releasefähig. Ein echter Windows-Installer-EXE wurde in dieser Linux-Umgebung nicht gebaut, weil dafür PyInstaller/Windows und Inno Setup auf Windows benötigt werden. Die Build- und Installer-Skripte sind vorbereitet.

## Kritischer Versionsvergleich

### v0.2.63 — Stärken

- Stärkeres Windows-Packaging.
- PyInstaller-Spec und Build-Skript vorhanden.
- Datenbank-Migrationen robuster.
- Schreibproben- und Enthusiast-Lab-Logik vollständiger.
- Tests für Packaging und Migration vorhanden.

### v0.2.64 — Stärken

- Wishlist-Bridge-Hotfix vorhanden.
- BudgetManager-Sparziel-Brücke vorhanden.
- Outbox-Export nach relevanten Ausgabenaktionen vorhanden.
- Bridge-Einstellungen im UI vorhanden.

### v0.2.64 — Regressionen gegenüber v0.2.63

- Packaging-/Installer-Struktur aus v0.2.63 nicht vollständig enthalten.
- Datenbank-Schema-Versionierung und Migrationshärtung teilweise verloren.
- Tinten-Restmengenlogik und Nachkaufempfehlungen teilweise verloren.
- Schreibprobenvergleich wurde vereinfacht und konnte problematische Samples zu stark gewichten.
- Federhistorie-/Legacy-Migrationen waren nicht vollständig im neuesten Stand.

## Umgesetzte Korrekturen

### Datenpfad-Logik

Neue Priorität:

1. `FPM_DATA_DIR` — Portable Startskripte und manuelle Overrides.
2. `installation.json` neben der App — Installer-Build mit gewähltem Datenordner.
3. `~/.fpm_data` — sicherer Fallback.

Damit schreiben Portable-Versionen nicht mehr versehentlich in den normalen Benutzerordner, wenn sie über die Startskripte gestartet werden.

### Updatemanager

Neu hinzugefügt:

- `updater/common.py`
- `updater/check_update.py`
- `updater/apply_update.py`
- `updater/generate_manifest.py`
- `updater/github_manifest.py`
- `updater/startup_check.py`
- `ui/update_dialog.py`

Eigenschaften:

- Manifest-Vertrag über `latest.json`.
- SHA256 ist Pflicht.
- Installer-Installationen bevorzugen `windows_installer`.
- Portable Installationen bevorzugen portable ZIPs.
- Update-Dialog ist in den Einstellungen eingebunden.
- Startparameter `--check-update` und `--apply-update` sind angebunden.

### Installer

Neu hinzugefügt:

- `installer/FountainPenManager_Setup.iss`

Eigenschaften:

- BudgetManager-ähnlicher Installer.
- Datenordnerauswahl.
- `installation.json` im App-Ordner.
- `config.json` im Datenordner für Initialwerte.
- Support für `/DATA_DIR=...` und `/UPDATE_MODE=1`.
- Mehrsprachige Installer-Texte Deutsch/Englisch/Französisch.

### Portable

Neu hinzugefügt/gehärtet:

- Portable Windows-ZIP mit `start-windows.cmd`.
- Portable Linux-ZIP mit `start-linux.sh`.
- Datenordner `./data` inklusive Backups.
- Starter setzen `FPM_DATA_DIR` korrekt.

### Build/Release

Neu/überarbeitet:

- `tools/build_windows.py`
- `tools/build_release_assets.py`
- `tools/sync_version.py`
- `.github/workflows/windows-release.yml`
- `FPM.spec`
- `latest.json.template`
- `docs/latest.json.template`

## Testprotokoll

Ausgeführt im Quellordner:

```bash
python -m compileall -q .
python -m pytest -q
python tools/sync_version.py --check
python tools/i18n_audit.py
python tools/i18n_quality_audit.py
python tools/i18n_key_wiring_audit.py
python tools/i18n_runtime_audit.py
python tools/i18n_visible_text_audit.py
```

Ergebnis:

- 86 Tests bestanden.
- Versionsdateien synchron: 0.2.65.
- I18N vollständig für DE/EN/FR.
- Keine kritischen Audit-Funde.

## Releasefähigkeit

### Quellcode

Status: releasefähig als RC.

### Portable

Status: Build-Skripte vorhanden und statisch geprüft. Finales Windows-/Linux-Portable-ZIP muss auf der jeweiligen Build-Umgebung erzeugt werden.

### Installer

Status: Installer-Skript vorhanden. Finales Setup-EXE muss auf Windows mit Inno Setup gebaut werden.

### Updater

Status: Architektur integriert. Produktiv nutzbar nach Eintragen des echten GitHub-Links und Upload der Release-Assets plus `latest.json`.

## GitHub-Checkliste vor erstem echten Release

1. Repository erstellen.
2. `sloogy/FPM` durch echten Pfad ersetzen.
3. Tag setzen, z. B. `v0.2.65`.
4. GitHub Actions Release-Build laufen lassen.
5. Prüfen, dass Release diese Assets enthält:
   - `latest.json`
   - `SHA256SUMS.txt`
   - `FountainPenManager-v0.2.65-portable-windows.zip`
   - optional `FountainPenManager-v0.2.65-portable-linux.zip`
   - `FountainPenManager_Setup_0.2.65.exe`
   - `FountainPenManager_Setup_0.2.65.zip`
6. In-App-Updater gegen `latest.json` testen.
