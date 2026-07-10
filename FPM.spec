# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller onedir spec for FountainPen Manager.

Build on Windows for Windows releases:
    pyinstaller FPM.spec --noconfirm --clean

The app keeps user data outside the executable by default. Portable launchers set
FPM_DATA_DIR to a local data/ folder next to the executable.
"""
from pathlib import Path

ROOT = Path(SPECPATH)
block_cipher = None

# Local translation JSON files must be available at runtime because
# i18n/translator.py loads them via Path(__file__).parent / "<lang>.json".
datas = [
    (str(ROOT / "i18n" / "de.json"), "i18n"),
    (str(ROOT / "i18n" / "en.json"), "i18n"),
    (str(ROOT / "i18n" / "fr.json"), "i18n"),
    (str(ROOT / "README.md"), "."),
    (str(ROOT / "version.json"), "."),
    (str(ROOT / "docs" / "BENUTZERHANDBUCH_DE.md"), "docs"),
]

hiddenimports = [
    "sqlalchemy.dialects.sqlite",
    "updater.check_update",
    "updater.apply_update",
    "updater.common",
    "requests",
    "packaging.version",
]


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
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "assets" / "fountainpen.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="FountainPenManager",
)
