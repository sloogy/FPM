# Windows-Release bauen

## Ziel

Dieses Release erzeugt wie beim BudgetTool zwei Windows-Artefakte:

- `FountainPenManager-v0.3.05-portable-windows.zip`
- `FountainPenManager_Setup_0.3.05.exe`

Zusätzlich werden erzeugt:

- `FountainPenManager_Setup_0.3.05.zip`
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

Ein nummerierter Tag wie `v0.3.05-rc.2` führt die echten Windows-/Linux-Builds, den Installer und beide LifePlanner-Module ohne Signier-Keys aus. Die Ergebnisse werden klar als unsigned GitHub-Prerelease veröffentlicht, jedoch ohne `latest.json`. Die `.lpmodule` sind für manuelle Tests unsigniert und benötigen in LifePlanner eine ausdrückliche Vertrauensbestätigung. Nur der exakte finale Tag `v0.3.05` verlangt Authenticode- und LifePlanner-Keys und darf den stabilen Release veröffentlichen.

## Enterprise-Freigabe v0.3.05

Offizielle Tag-Releases werden nur mit den getrennten Hash-Locks `constraints-windows.lock` und `constraints-linux.lock` gebaut. Die Windows-App und der Installer müssen mit Authenticode signiert und durch `signtool verify /pa /all /v` bestätigt sein. Fehlen Lockdatei, CI-Gate oder Signatur-Secrets, bricht der Workflow ohne Fallback ab. Details stehen in `ENTERPRISE_RELEASE_RUNBOOK_DE.md`.
