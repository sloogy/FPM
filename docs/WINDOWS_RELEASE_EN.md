# Building the Windows release

## Goal

This release produces two Windows artifacts, following the BudgetTool release model:

- `FountainPenManager-v1.2.2-portable-windows.zip`
- `FountainPenManager_Setup_1.2.2.exe`

It also creates:

- `FountainPenManager_Setup_1.2.2.zip`
- `latest.json`
- `SHA256SUMS.txt`

## Build locally on Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-build.txt
python tools\build_windows.py --clean
```

Inno Setup 6 is required for the installer. To build only the portable ZIP when Inno Setup is missing:

```powershell
python tools\build_windows.py --clean --skip-installer-if-missing
```

## Portable mode

The portable ZIP contains `start-windows.cmd`. This launcher sets:

```text
FPM_DATA_DIR=<portable folder>\data
```

Database, configuration and backups therefore stay inside the portable folder.

## Installer mode

The installer installs the app into `Program Files/FountainPen Manager`. User data remains in the user profile under `.fpm_data`, so updates or uninstalling the app do not delete the collection database.

## GitHub Actions

The workflow `.github/workflows/windows-release.yml` builds on `windows-latest`:

1. Tests and i18n audits
2. PyInstaller onedir build
3. Portable ZIP
4. Inno Setup installer
5. SHA256SUMS and `latest.json`
6. Artifact upload and GitHub Release upload for tags

A numbered tag such as `v1.2.2-rc.2` runs the real Windows/Linux builds, installer, and both LifePlanner/LiveManager modules without signing keys. The results are published as a clearly marked unsigned GitHub Prerelease without `latest.json`. The exact final tag `v1.2.2` publishes a normal unsigned release after the same gates, including `latest.json` and `UNSIGNED_RELEASE.txt`. Local `.lpmodule` installation requires explicit trust confirmation.

## Enterprise release gate v1.2.2

Official tagged releases are built only from the separate hash locks `constraints-windows.lock` and `constraints-linux.lock`. The Windows application, installer, and `.lpmodule` files are explicitly unsigned for this release; signing secrets are not required. Missing locks, CI gates, checksums, warnings, or host test installations stop the workflow.
