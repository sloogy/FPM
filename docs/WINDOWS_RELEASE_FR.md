# Créer la version Windows

## Objectif

Cette version crée deux artefacts Windows, selon le modèle du BudgetTool :

- `FountainPenManager-v1.0.8-portable-windows.zip`
- `FountainPenManager_Setup_1.0.8.exe`

Elle crée aussi :

- `FountainPenManager_Setup_1.0.8.zip`
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

Un tag numéroté tel que `v1.0.8-rc.2` exécute les véritables builds Windows/Linux, l’installeur et les deux modules LifePlanner/LiveManager sans clés de signature. Les résultats sont publiés comme GitHub Prerelease clairement non signée, sans `latest.json`. Le tag final exact `v1.0.8` publie après les mêmes contrôles une version normale non signée avec `latest.json` et `UNSIGNED_RELEASE.txt`. L’installation locale des fichiers `.lpmodule` exige une confirmation explicite de confiance.

## Validation Enterprise v1.0.8

Les versions officielles étiquetées sont construites uniquement avec les verrous hachés séparés `constraints-windows.lock` et `constraints-linux.lock`. L’application Windows, l’installeur et les fichiers `.lpmodule` sont explicitement non signés pour cette version ; aucun secret de signature n’est requis. L’absence d’un verrou, d’un contrôle CI, de sommes de contrôle, d’un avertissement ou d’une installation de test par l’hôte bloque le workflow.
