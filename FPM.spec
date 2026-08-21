# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller onedir spec for FountainPen Manager.

Used by the cross-platform GitHub release workflow and for local builds:

    python -m PyInstaller FPM.spec --noconfirm --clean

Produces:
    dist/FountainPenManager/FountainPenManager.exe  (Windows)
    dist/FountainPenManager/FountainPenManager      (Linux)

User data is kept outside the executable by default. Portable launchers set
FPM_DATA_DIR to a local data/ folder next to the executable.
"""

import sys
from pathlib import Path

ROOT = Path(SPECPATH)
block_cipher = None

# Local translation JSON files must be available at runtime because
# i18n/translator.py loads them via Path(__file__).parent / "<lang>.json".
datas = [
    (str(ROOT / "i18n" / "de.json"), "i18n"),
    (str(ROOT / "i18n" / "en.json"), "i18n"),
    (str(ROOT / "i18n" / "fr.json"), "i18n"),
    # Theme profiles are loaded from disk at runtime just like the locales.
    # Without them only the two built-in profiles remain.
    *[(str(path), "ui/profiles")
      for path in sorted((ROOT / "ui" / "profiles").glob("*.json"))],
    (str(ROOT / "README.md"), "."),
    (str(ROOT / "version.json"), "."),
    (str(ROOT / "docs" / "BENUTZERHANDBUCH_DE.md"), "docs"),
    (str(ROOT / "docs" / "USER_MANUAL_EN.md"), "docs"),
    (str(ROOT / "docs" / "MANUEL_UTILISATEUR_FR.md"), "docs"),
]

# Vertrauensanker fuer die Update-Manifest-Signatur. Der Release-Workflow legt
# die Datei vorher mit tools/materialize_update_public_key.py an. Fehlt sie,
# entsteht ein Build, der jedes Update ablehnt - das ist gewollt fail-closed,
# aber es soll niemandem unbemerkt passieren, darum der Hinweis.
_update_public_key = ROOT / "resources" / "update_signing_public_key.b64"
if _update_public_key.is_file():
    datas.append((str(_update_public_key), "resources"))
else:
    print(
        "Hinweis: Build ohne Update-Vertrauensanker - dieser Stand nimmt keine "
        "Updates an. Fuer ein Release zuerst "
        "tools/materialize_update_public_key.py ausfuehren."
    )

hiddenimports = [
    "sqlalchemy.dialects.sqlite",
    "updater.check_update",
    "updater.apply_update",
    "updater.common",
    "updater.manifest_signing",
    "packaging.version",
]

# The ICO is required for Windows. Linux builds do not need a Windows icon and
# should not fail when the platform toolchain cannot process it.
icon_path = (
    str(ROOT / "assets" / "fountainpen.ico")
    if sys.platform.startswith("win")
    else None
)


a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "unittest", "pydoc", "doctest"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="FountainPenManager",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="FountainPenManager",
)
