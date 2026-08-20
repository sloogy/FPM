#!/usr/bin/env python3
"""Build combined Windows and Linux GitHub release assets for FPM.

This script consumes two PyInstaller onedir bundles plus the Windows installer
and creates:

- FountainPenManager-v<version>-portable-windows.zip
- FountainPenManager-v<version>-portable-linux.zip
- FountainPenManager_Setup_<version>.exe
- FountainPenManager_Setup_<version>.zip
- fpm_<version>_Windows_x86_64.lpmodule
- fpm_<version>_Linux_x86_64.lpmodule
- latest.json
- SHA256SUMS.txt

It deliberately uses only the Python standard library so the manifest job does
not require the application runtime dependencies.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import stat
import sys
import zipfile
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app_info import APP_NAME, APP_VERSION

WINDOWS_BINARY = "FountainPenManager.exe"
LINUX_BINARY = "FountainPenManager"


def die(message: str) -> None:
    raise SystemExit(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def first_existing(candidates: Iterable[Path]) -> Path | None:
    for path in candidates:
        if path.is_file():
            return path
    return None


def find_binary(build_dir: Path, filename: str) -> Path:
    direct = first_existing(
        (
            build_dir / filename,
            build_dir / "dist" / filename,
            build_dir / "FountainPenManager" / filename,
        )
    )
    if direct:
        return direct

    matches = sorted(path for path in build_dir.rglob(filename) if path.is_file())
    if matches:
        return matches[0]

    die(f"{filename} wurde nicht gefunden in: {build_dir}")


def find_installer(installer_dir: Path) -> Path:
    direct = first_existing(
        (
            installer_dir / "FountainPenManager_Setup.exe",
            installer_dir / "release" / "FountainPenManager_Setup.exe",
        )
    )
    if direct:
        return direct

    matches = sorted(installer_dir.rglob("FountainPenManager_Setup*.exe"))
    if matches:
        return matches[0]

    die(f"Windows-Installer wurde nicht gefunden in: {installer_dir}")


def copy_bundle(binary: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)

    shutil.copytree(binary.parent, destination)

    copied_binary = destination / binary.name
    if not copied_binary.is_file():
        die(f"Bundle enthält die Programmdatei nicht: {copied_binary}")

    if not (destination / "_internal").is_dir():
        die(f"PyInstaller-onedir-Bundle ohne _internal/: {destination}")


def write_zip(
    zip_path: Path,
    source_dir: Path,
    *,
    executable_names: frozenset[str] = frozenset(),
) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    zip_path.unlink(missing_ok=True)

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source_dir.rglob("*")):
            if path.is_file():
                archive_name = path.relative_to(source_dir).as_posix()
                info = zipfile.ZipInfo.from_file(path, archive_name)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                mode = path.stat().st_mode
                if archive_name in executable_names:
                    mode |= stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
                info.external_attr = (mode & 0xFFFF) << 16
                with path.open("rb") as source, archive.open(info, "w") as target:
                    shutil.copyfileobj(source, target, length=1024 * 1024)


def write_windows_starter(path: Path) -> None:
    path.write_text(
        "@echo off\r\n"
        "setlocal EnableExtensions\r\n"
        'set "DIR=%~dp0"\r\n'
        'set "FPM_DATA_DIR=%DIR%data"\r\n'
        'if not exist "%FPM_DATA_DIR%" mkdir "%FPM_DATA_DIR%"\r\n'
        'set "QT_ENABLE_HIGHDPI_SCALING=1"\r\n'
        'set "QT_AUTO_SCREEN_SCALE_FACTOR=1"\r\n'
        'set "QT_SCALE_FACTOR_ROUNDING_POLICY=PassThrough"\r\n'
        f'if not exist "%DIR%{WINDOWS_BINARY}" (\r\n'
        f'  echo {WINDOWS_BINARY} wurde nicht gefunden.\r\n'
        "  exit /b 1\r\n"
        ")\r\n"
        f'start "" "%DIR%{WINDOWS_BINARY}" %*\r\n',
        encoding="utf-8",
        newline="",
    )


def write_linux_starter(path: Path) -> None:
    path.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'DIR="$(cd "$(dirname "$0")" && pwd)"\n'
        'export FPM_DATA_DIR="${FPM_DATA_DIR:-$DIR/data}"\n'
        'export QT_ENABLE_HIGHDPI_SCALING="${QT_ENABLE_HIGHDPI_SCALING:-1}"\n'
        'export QT_AUTO_SCREEN_SCALE_FACTOR="${QT_AUTO_SCREEN_SCALE_FACTOR:-1}"\n'
        'export QT_SCALE_FACTOR_ROUNDING_POLICY="${QT_SCALE_FACTOR_ROUNDING_POLICY:-PassThrough}"\n'
        'mkdir -p "$FPM_DATA_DIR"\n'
        f'chmod +x "$DIR/{LINUX_BINARY}" 2>/dev/null || true\n'
        f'exec "$DIR/{LINUX_BINARY}" "$@"\n',
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def write_readme(path: Path, version: str, platform_name: str) -> None:
    starter = "start-windows.cmd" if platform_name == "windows" else "./start-linux.sh"
    path.write_text(
        f"FountainPen Manager {version} — Portable {platform_name}\n"
        "================================================\n\n"
        f"Start: {starter}\n\n"
        "Datenbank, Einstellungen und Backups werden in ./data gespeichert.\n"
        "Die Programmdatei und der Ordner _internal/ müssen zusammenbleiben.\n",
        encoding="utf-8",
    )


def create_portable_zip(
    *,
    build_dir: Path,
    output_dir: Path,
    version: str,
    platform_name: str,
) -> Path:
    binary_name = WINDOWS_BINARY if platform_name == "windows" else LINUX_BINARY
    binary = find_binary(build_dir, binary_name)
    work = output_dir / f"_portable_{platform_name}"

    copy_bundle(binary, work)

    target_binary = work / binary_name
    if platform_name == "linux":
        target_binary.chmod(
            target_binary.stat().st_mode
            | stat.S_IXUSR
            | stat.S_IXGRP
            | stat.S_IXOTH
        )

    (work / "data" / "backups").mkdir(parents=True, exist_ok=True)
    (work / "data" / ".keep").touch()
    (work / "data" / "backups" / ".keep").touch()

    if platform_name == "windows":
        write_windows_starter(work / "start-windows.cmd")
    else:
        write_linux_starter(work / "start-linux.sh")

    write_readme(work / "README.txt", version, platform_name)

    zip_path = output_dir / (
        f"FountainPenManager-v{version}-portable-{platform_name}.zip"
    )
    executable_names = (
        frozenset({LINUX_BINARY, "start-linux.sh"})
        if platform_name == "linux"
        else frozenset()
    )
    write_zip(zip_path, work, executable_names=executable_names)
    shutil.rmtree(work)
    return zip_path


def create_installer_assets(
    *, installer_dir: Path, output_dir: Path, version: str, signed: bool
) -> tuple[Path, Path]:
    source = find_installer(installer_dir)
    normalized = output_dir / f"FountainPenManager_Setup_{version}.exe"
    shutil.copy2(source, normalized)

    work = output_dir / "_installer_zip"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    shutil.copy2(normalized, work / normalized.name)
    signature_notice = (
        "Der Installer ist Authenticode-signiert und wurde vor der "
        "Veröffentlichung mit signtool geprüft.\n"
        if signed
        else "Dieser Prerelease-Installer ist nicht digital signiert.\n"
    )
    (work / "WINDOWS_DOWNLOAD_HINWEIS.txt").write_text(
        "FountainPen Manager Windows-Download\n"
        "====================================\n\n"
        f"{signature_notice}"
        "SHA256SUMS.txt kann zur Integritätsprüfung verwendet werden.\n",
        encoding="utf-8",
    )

    installer_zip = output_dir / f"FountainPenManager_Setup_{version}.zip"
    write_zip(installer_zip, work)
    shutil.rmtree(work)
    return normalized, installer_zip


def copy_module_asset(
    source: Path,
    output_dir: Path,
    expected_name: str,
    *,
    require_signature: bool,
) -> Path:
    source = source.resolve()
    if not source.is_file():
        die(f"LifePlanner module asset missing: {source}")
    target = output_dir / expected_name
    shutil.copy2(source, target)
    with zipfile.ZipFile(target) as archive:
        names = set(archive.namelist())
        if {"component.json", "payload/module.json"} - names:
            die(f"{target.name}: incomplete LifePlanner module archive")
        has_signature = "component.json.sig" in names
        if require_signature and not has_signature:
            die(f"{target.name}: stable LifePlanner module is not signed")
        if not require_signature and has_signature:
            die(f"{target.name}: prerelease LifePlanner module must stay unsigned")
    return target


def asset(base_url: str, path: Path, asset_type: str) -> dict[str, str]:
    return {
        "type": asset_type,
        "url": f"{base_url.rstrip('/')}/{path.name}",
        "sha256": sha256_file(path),
    }


def validate_portable_zip(
    zip_path: Path, *, binary_name: str, starter_name: str
) -> None:
    with zipfile.ZipFile(zip_path) as archive:
        names = set(archive.namelist())

    required = {
        binary_name,
        starter_name,
        "data/.keep",
        "data/backups/.keep",
    }
    missing = required - names
    if missing:
        die(f"{zip_path.name}: fehlende Dateien: {sorted(missing)}")

    if not any(name.startswith("_internal/") for name in names):
        die(f"{zip_path.name}: _internal/ fehlt")


def write_checksums(output_dir: Path) -> None:
    checksum_files = sorted(
        path
        for path in output_dir.iterdir()
        if path.is_file() and path.name != "SHA256SUMS.txt"
    )
    (output_dir / "SHA256SUMS.txt").write_text(
        "".join(
            f"{sha256_file(path)}  {path.name}\n"
            for path in checksum_files
        ),
        encoding="ascii",
    )


def print_created_assets(output_dir: Path, label: str) -> None:
    print(f"{label} assets created:")
    for path in sorted(output_dir.iterdir()):
        if path.is_file():
            print(f"  {path.name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--release-tag", required=True)
    parser.add_argument("--base-url")
    parser.add_argument("--windows-build-dir", type=Path, required=True)
    parser.add_argument("--linux-build-dir", type=Path, required=True)
    parser.add_argument("--installer-dir", type=Path, required=True)
    parser.add_argument("--module-windows", type=Path)
    parser.add_argument("--module-linux", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--prerelease", action="store_true")
    args = parser.parse_args()

    expected_tag = f"v{args.version}"
    if args.version != APP_VERSION:
        die(
            f"Version mismatch: app_info.py={APP_VERSION}, "
            f"argument={args.version}"
        )
    rc_suffix = args.release_tag.removeprefix(expected_tag + "-rc.")
    valid_rc_tag = (
        args.release_tag.startswith(expected_tag + "-rc.")
        and rc_suffix.isdecimal()
        and int(rc_suffix) >= 1
        and str(int(rc_suffix)) == rc_suffix
    )
    if args.prerelease and not valid_rc_tag:
        die(
            f"Prerelease tag mismatch: expected {expected_tag}-rc.N, "
            f"got {args.release_tag}"
        )
    if not args.prerelease and args.release_tag != expected_tag:
        die(
            f"Tag mismatch: expected {expected_tag}, "
            f"got {args.release_tag}"
        )
    if not args.module_windows or not args.module_linux:
        die("All releases require both LifePlanner module assets")
    if not args.prerelease and not args.base_url:
        die("Stable releases require a base URL")

    output_dir = args.out_dir.resolve()
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    asset_version = (
        args.release_tag.removeprefix("v") if args.prerelease else args.version
    )
    windows_zip = create_portable_zip(
        build_dir=args.windows_build_dir.resolve(),
        output_dir=output_dir,
        version=asset_version,
        platform_name="windows",
    )
    linux_zip = create_portable_zip(
        build_dir=args.linux_build_dir.resolve(),
        output_dir=output_dir,
        version=asset_version,
        platform_name="linux",
    )
    installer_exe, installer_zip = create_installer_assets(
        installer_dir=args.installer_dir.resolve(),
        output_dir=output_dir,
        version=asset_version,
        signed=not args.prerelease,
    )

    validate_portable_zip(
        windows_zip,
        binary_name=WINDOWS_BINARY,
        starter_name="start-windows.cmd",
    )
    validate_portable_zip(
        linux_zip,
        binary_name=LINUX_BINARY,
        starter_name="start-linux.sh",
    )

    module_manifest = json.loads((ROOT / "module.json").read_text(encoding="utf-8"))
    if module_manifest.get("version") != args.version:
        die("module.json version does not match release version")
    module_id = module_manifest["id"]
    module_windows = copy_module_asset(
        args.module_windows,
        output_dir,
        f"{module_id}_{args.version}_Windows_x86_64.lpmodule",
        require_signature=not args.prerelease,
    )
    module_linux = copy_module_asset(
        args.module_linux,
        output_dir,
        f"{module_id}_{args.version}_Linux_x86_64.lpmodule",
        require_signature=not args.prerelease,
    )

    if args.prerelease:
        (output_dir / "UNSIGNED_PRERELEASE.txt").write_text(
            f"FountainPen Manager {args.release_tag}\n"
            "=====================================\n\n"
            "UNSIGNED TEST BUILD / NICHT SIGNIERTER TESTBUILD\n\n"
            "Dieses Prerelease dient ausschließlich der Funktionsprüfung. "
            "Windows kann deshalb eine Sicherheitswarnung anzeigen. Die "
            "beiden LifePlanner-.lpmodule-Pakete sind ebenfalls unsigniert "
            "und benötigen bei lokaler Installation eine ausdrückliche "
            "Vertrauensbestätigung. Die finale Version wird erst nach "
            "erfolgreicher Prüfung mit Authenticode- und LifePlanner-Keys "
            "veröffentlicht.\n",
            encoding="utf-8",
        )
        write_checksums(output_dir)
        print_created_assets(output_dir, "Prerelease")
        return 0

    assets = {
        "windows": asset(args.base_url, windows_zip, "portable-zip"),
        "linux": asset(args.base_url, linux_zip, "portable-zip"),
        "portable_windows_zip": asset(
            args.base_url, windows_zip, "portable-zip"
        ),
        "portable_linux_zip": asset(
            args.base_url, linux_zip, "portable-zip"
        ),
        "portable_zip": asset(args.base_url, windows_zip, "portable-zip"),
        "windows_installer": asset(
            args.base_url, installer_exe, "installer"
        ),
        "windows_installer_zip": asset(
            args.base_url, installer_zip, "installer-zip"
        ),
        "lifeplanner_windows": asset(
            args.base_url, module_windows, "lifeplanner-module"
        ),
        "lifeplanner_linux": asset(
            args.base_url, module_linux, "lifeplanner-module"
        ),
    }

    manifest = {
        "app": APP_NAME,
        "channel": "stable",
        "version": args.version,
        "release_tag": args.release_tag,
        "assets": assets,
    }
    latest_json = output_dir / "latest.json"
    latest_json.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    write_checksums(output_dir)
    print_created_assets(output_dir, "Release")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
