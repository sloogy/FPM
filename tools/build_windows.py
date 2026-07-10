#!/usr/bin/env python3
"""Build Windows portable ZIP and optional Inno Setup installer.

Outputs in release/:
- FountainPenManager-v<version>-portable-windows.zip
- FountainPenManager_Setup_<version>.exe (if ISCC is available)
- FountainPenManager_Setup_<version>.zip
- latest.json with URL+SHA256 fields for the in-app updater
- SHA256SUMS.txt
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app_info import APP_NAME, APP_VERSION  # noqa: E402

APP_EXE = "FountainPenManager.exe"
DIST_DIR = ROOT / "dist" / "FountainPenManager"
BUILD_DIR = ROOT / "build"
RELEASE_DIR = ROOT / "release"
PORTABLE_NAME = f"FountainPenManager-v{APP_VERSION}-portable-windows"
PORTABLE_DIR = RELEASE_DIR / PORTABLE_NAME
SPEC_PATH = ROOT / "FPM.spec"
ISS_PATH = ROOT / "installer" / "FountainPenManager_Setup.iss"
DEFAULT_BASE_URL = f"https://github.com/sloogy/FPM/releases/download/v{APP_VERSION}"


def run(cmd: list[str], *, cwd: Path = ROOT) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=cwd, check=True)


def remove(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def ensure_clean() -> None:
    remove(DIST_DIR.parent)
    remove(BUILD_DIR)
    remove(RELEASE_DIR)
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)


def build_pyinstaller() -> None:
    if not SPEC_PATH.exists():
        raise SystemExit(f"PyInstaller spec missing: {SPEC_PATH}")
    run([sys.executable, "-m", "PyInstaller", str(SPEC_PATH), "--noconfirm", "--clean"])
    exe = DIST_DIR / APP_EXE
    if not exe.exists():
        raise SystemExit(f"Build failed: missing {exe}")


def write_portable_launchers(portable: Path) -> None:
    data_dir = portable / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / ".keep").write_text("Portable user data lives here.\n", encoding="utf-8")
    (data_dir / "backups").mkdir(exist_ok=True)
    (data_dir / "backups" / ".keep").write_text("Portable backups live here.\n", encoding="utf-8")
    (portable / "VERSION.txt").write_text(APP_VERSION + "\n", encoding="utf-8")
    docs_dir = portable / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "docs" / "BENUTZERHANDBUCH_DE.md", docs_dir / "BENUTZERHANDBUCH_DE.md")
    (portable / "README_PORTABLE.txt").write_text(
        f"{APP_NAME} portable Windows build v{APP_VERSION}\n\n"
        "Start: double-click start-windows.cmd or FountainPenManager.exe.\n\n"
        "The launcher sets FPM_DATA_DIR to the local data/ folder, so database,\n"
        "config, backups and update cache stay inside this portable directory.\n"
        "This ZIP is also the updater package; do not rename FountainPenManager.exe\n"
        "inside the ZIP.\n",
        encoding="utf-8",
    )
    (portable / "start-windows.cmd").write_text(
        "@echo off\r\n"
        "setlocal EnableExtensions\r\n"
        "set \"DIR=%~dp0\"\r\n"
        "set \"FPM_DATA_DIR=%DIR%data\"\r\n"
        "if not exist \"%FPM_DATA_DIR%\" mkdir \"%FPM_DATA_DIR%\"\r\n"
        "set \"QT_ENABLE_HIGHDPI_SCALING=1\"\r\n"
        "set \"QT_AUTO_SCREEN_SCALE_FACTOR=1\"\r\n"
        "set \"QT_SCALE_FACTOR_ROUNDING_POLICY=PassThrough\"\r\n"
        f"start \"FountainPen Manager\" \"%DIR%{APP_EXE}\" %*\r\n",
        encoding="utf-8",
        newline="",
    )


def make_portable_zip() -> Path:
    remove(PORTABLE_DIR)
    shutil.copytree(DIST_DIR, PORTABLE_DIR)
    write_portable_launchers(PORTABLE_DIR)
    zip_path = RELEASE_DIR / f"{PORTABLE_NAME}.zip"
    remove(zip_path)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(PORTABLE_DIR.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(RELEASE_DIR))
    return zip_path


def find_iscc() -> str | None:
    env = os.environ.get("ISCC")
    if env and Path(env).exists():
        return env
    found = shutil.which("ISCC.exe") or shutil.which("iscc.exe") or shutil.which("ISCC")
    if found:
        return found
    candidates = [
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("ProgramFiles", "")) / "Inno Setup 6" / "ISCC.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def build_installer(skip_if_missing: bool) -> Path | None:
    iscc = find_iscc()
    if not iscc:
        msg = "Inno Setup compiler ISCC.exe not found."
        if skip_if_missing:
            print("WARNING:", msg, "Installer skipped.")
            return None
        raise SystemExit(msg + " Install Inno Setup 6 or set ISCC=<path>.")
    run([iscc, str(ISS_PATH)])
    exe = RELEASE_DIR / f"FountainPenManager_Setup_{APP_VERSION}.exe"
    if not exe.exists():
        raise SystemExit(f"Installer build failed: missing {exe}")
    zip_path = RELEASE_DIR / f"FountainPenManager_Setup_{APP_VERSION}.zip"
    remove(zip_path)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(exe, exe.name)
        readme = RELEASE_DIR / "WINDOWS_DOWNLOAD_HINWEIS.txt"
        readme.write_text(
            "FountainPen Manager Windows-Download\n"
            "====================================\n\n"
            "Neue unsignierte Open-Source-Installer koennen von Browser/SmartScreen blockiert werden.\n"
            "SHA256 in SHA256SUMS.txt pruefen und bei SmartScreen: Weitere Informationen -> Trotzdem ausfuehren.\n",
            encoding="utf-8",
        )
        zf.write(readme, readme.name)
        readme.unlink(missing_ok=True)
    return exe


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _asset(base_url: str, path: Path, kind: str) -> dict[str, str]:
    return {"type": kind, "url": f"{base_url.rstrip('/')}/{path.name}", "sha256": sha256(path)}


def write_manifests(base_url: str) -> None:
    assets = sorted(
        p for p in RELEASE_DIR.iterdir()
        if p.is_file() and p.name not in {"SHA256SUMS.txt", "latest.json"}
    )
    (RELEASE_DIR / "SHA256SUMS.txt").write_text(
        "".join(f"{sha256(path)}  {path.name}\n" for path in assets),
        encoding="ascii",
    )

    portable = RELEASE_DIR / f"{PORTABLE_NAME}.zip"
    installer = RELEASE_DIR / f"FountainPenManager_Setup_{APP_VERSION}.exe"
    installer_zip = RELEASE_DIR / f"FountainPenManager_Setup_{APP_VERSION}.zip"
    manifest_assets: dict[str, dict[str, str]] = {
        "windows": _asset(base_url, portable, "portable-zip"),
        "portable_windows_zip": _asset(base_url, portable, "portable-zip"),
        "portable_zip": _asset(base_url, portable, "portable-zip"),
    }
    if installer.exists():
        manifest_assets["windows_installer"] = _asset(base_url, installer, "installer")
    if installer_zip.exists():
        manifest_assets["windows_installer_zip"] = _asset(base_url, installer_zip, "installer-zip")

    manifest = {
        "app": APP_NAME,
        "channel": "stable",
        "version": APP_VERSION,
        "release_tag": f"v{APP_VERSION}",
        "assets": manifest_assets,
    }
    (RELEASE_DIR / "latest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_release() -> None:
    portable_zip = RELEASE_DIR / f"{PORTABLE_NAME}.zip"
    if not portable_zip.exists():
        raise SystemExit("Portable ZIP missing")
    with zipfile.ZipFile(portable_zip) as zf:
        names = set(zf.namelist())
        required = {
            f"{PORTABLE_NAME}/FountainPenManager.exe",
            f"{PORTABLE_NAME}/start-windows.cmd",
            f"{PORTABLE_NAME}/data/.keep",
            f"{PORTABLE_NAME}/data/backups/.keep",
            f"{PORTABLE_NAME}/_internal/i18n/de.json",
            f"{PORTABLE_NAME}/_internal/i18n/en.json",
            f"{PORTABLE_NAME}/_internal/i18n/fr.json",
            f"{PORTABLE_NAME}/VERSION.txt",
        }
        missing = sorted(required - names)
        if missing:
            raise SystemExit("Portable ZIP missing entries: " + ", ".join(missing))
    if not (RELEASE_DIR / "SHA256SUMS.txt").exists():
        raise SystemExit("SHA256SUMS.txt missing")
    if not (RELEASE_DIR / "latest.json").exists():
        raise SystemExit("latest.json missing")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean", action="store_true", help="Remove build/dist/release before building")
    parser.add_argument("--skip-installer", action="store_true", help="Do not run Inno Setup")
    parser.add_argument("--skip-installer-if-missing", action="store_true", help="Build portable ZIP even when ISCC.exe is unavailable")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Release download base URL for latest.json")
    args = parser.parse_args(argv)

    if args.clean:
        ensure_clean()
    else:
        RELEASE_DIR.mkdir(parents=True, exist_ok=True)

    build_pyinstaller()
    make_portable_zip()
    if not args.skip_installer:
        build_installer(skip_if_missing=args.skip_installer_if_missing)
    write_manifests(args.base_url)
    validate_release()
    print(f"Release assets written to: {RELEASE_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
