# Windows-Release bauen

## Ziel

Dieses Release erzeugt wie beim BudgetTool zwei Windows-Artefakte:

- `FountainPenManager-v1.0.6-portable-windows.zip`
- `FountainPenManager_Setup_1.0.6.exe`

Zusätzlich werden erzeugt:

- `FountainPenManager_Setup_1.0.6.zip`
- `latest.json`
- `SHA256SUMS.txt`

## Lokal auf Windows bauen

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-build.txt
python tools\build_windows.py --clean
```

Für den Installer muss Inno Setup 6 installiert sein. Ohne Inno Setup kann nur das Portable-ZIP gebaut werden:

```powershell
python tools\build_windows.py --clean --skip-installer-if-missing
```

## Portable-Modus

Das Portable-ZIP enthält `start-windows.cmd`. Dieser Starter setzt automatisch:

```text
FPM_DATA_DIR=<Portable-Ordner>\data
```

Dadurch bleiben Datenbank, Konfiguration und Backups im Portable-Ordner.

## Installer-Modus

Der Installer installiert die App nach `Programme/FountainPen Manager`. Daten liegen standardmäßig im Benutzerprofil unter `.fpm_data`. Das ist gewollt, damit Updates oder Deinstallationen die Sammlungsdaten nicht löschen.

## GitHub Actions

Der Workflow `.github/workflows/windows-release.yml` baut auf `windows-latest`:

1. Tests und i18n-Audits
2. PyInstaller-Onedir
3. Portable-ZIP
4. Inno-Setup-Installer
5. SHA256SUMS und `latest.json`
6. Upload als Artifact und bei Tags als GitHub Release Asset

Ein nummerierter Tag wie `v1.0.6-rc.2` führt die echten Windows-/Linux-Builds, den Installer und beide LifePlanner-/LiveManager-Module ohne Signier-Keys aus. Die Ergebnisse werden klar als unsigned GitHub-Prerelease veröffentlicht, jedoch ohne `latest.json`. Der exakte finale Tag `v1.0.6` veröffentlicht nach denselben Gates einen normalen unsigned Release mit `latest.json` und `UNSIGNED_RELEASE.txt`. Die `.lpmodule` benötigen bei lokaler Installation eine ausdrückliche Vertrauensbestätigung.

## Enterprise-Freigabe v1.0.6

Offizielle Tag-Releases werden nur mit den getrennten Hash-Locks `constraints-windows.lock` und `constraints-linux.lock` gebaut. Windows-App, Installer und `.lpmodule` sind in diesem Release ausdrücklich unsigned; Signatur-Secrets werden nicht benötigt. Fehlende Lockdateien, CI-Gates, Checksummen, Warnhinweise oder Host-Testinstallationen brechen den Workflow ab. Details stehen in `ENTERPRISE_RELEASE_RUNBOOK_DE.md`.
