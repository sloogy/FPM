# Créer la version Windows

## Objectif

Cette version crée deux artefacts Windows, selon le modèle du BudgetTool :

- `FountainPenManager-v0.3.05-portable-windows.zip`
- `FountainPenManager_Setup_0.3.05.exe`

Elle crée aussi :

- `FountainPenManager_Setup_0.3.05.zip`
- `latest.json`
- `SHA256SUMS.txt`

## Compilation locale sous Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-build.txt
python tools\build_windows.py --clean
```

Inno Setup 6 est nécessaire pour l’installateur. Sans Inno Setup, il est possible de créer seulement le ZIP portable :

```powershell
python tools\build_windows.py --clean --skip-installer-if-missing
```

## Mode portable

Le ZIP portable contient `start-windows.cmd`. Ce lanceur définit :

```text
FPM_DATA_DIR=<dossier portable>\data
```

La base de données, la configuration et les sauvegardes restent donc dans le dossier portable.

## Mode installateur

L’installateur installe l’application dans `Program Files/FountainPen Manager`. Les données utilisateur restent dans le profil utilisateur sous `.fpm_data`, afin qu’une mise à jour ou une désinstallation ne supprime pas la base de données de collection.

## GitHub Actions

Le workflow `.github/workflows/windows-release.yml` compile sur `windows-latest` :

1. Tests et audits i18n
2. Build PyInstaller onedir
3. ZIP portable
4. Installateur Inno Setup
5. SHA256SUMS et `latest.json`
6. Upload comme artefact et, pour les tags, comme asset GitHub Release

Un tag numéroté tel que `v0.3.05-rc.1` exécute les véritables builds Windows/Linux et l’installeur sans clés de signature. Les résultats sont publiés comme GitHub Prerelease clairement non signée, sans `latest.json` ni modules LifePlanner. Seul le tag final exact `v0.3.05` exige les clés Authenticode et LifePlanner et peut publier la version stable.

## Validation Enterprise v0.3.05

Les versions officielles étiquetées sont construites uniquement avec les verrous hachés séparés `constraints-windows.lock` et `constraints-linux.lock`. L’application Windows et l’installateur doivent être signés avec Authenticode et réussir `signtool verify /pa /all /v`. L’absence d’un verrou, d’un contrôle CI ou d’un secret de signature bloque le workflow sans solution de repli non sécurisée.
