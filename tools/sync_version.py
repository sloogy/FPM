#!/usr/bin/env python3
"""Synchronisiert APP_VERSION aus app_info.py in Release-Dateien.

Quelle: app_info.py
Aktualisiert/prueft:
- version.json
- VERSION_INFO.txt
- installer/FountainPenManager_Setup.iss
- latest.json.template
- docs/latest.json.template
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app_info import APP_NAME, APP_VERSION, APP_RELEASE_DATE, APP_BUILD  # noqa: E402


def _latest_template_data() -> dict:
    tag = f"v{APP_VERSION}"
    base = f"https://github.com/sloogy/FPM/releases/download/{tag}"
    return {
        "app": APP_NAME,
        "channel": "stable",
        "version": APP_VERSION,
        "release_tag": tag,
        "assets": {
            "windows": {
                "type": "portable-zip",
                "url": f"{base}/FountainPenManager-v{APP_VERSION}-portable-windows.zip",
                "sha256": "PUT_SHA256_HERE",
            },
            "linux": {
                "type": "portable-zip",
                "url": f"{base}/FountainPenManager-v{APP_VERSION}-portable-linux.zip",
                "sha256": "PUT_SHA256_HERE",
            },
            "portable_windows_zip": {
                "type": "portable-zip",
                "url": f"{base}/FountainPenManager-v{APP_VERSION}-portable-windows.zip",
                "sha256": "PUT_SHA256_HERE",
            },
            "portable_linux_zip": {
                "type": "portable-zip",
                "url": f"{base}/FountainPenManager-v{APP_VERSION}-portable-linux.zip",
                "sha256": "PUT_SHA256_HERE",
            },
            "portable_zip": {
                "type": "portable-zip",
                "url": f"{base}/FountainPenManager-v{APP_VERSION}-portable-windows.zip",
                "sha256": "PUT_SHA256_HERE",
            },
            "windows_installer": {
                "type": "installer",
                "url": f"{base}/FountainPenManager_Setup_{APP_VERSION}.exe",
                "sha256": "PUT_SHA256_HERE",
            },
            "windows_installer_zip": {
                "type": "installer-zip",
                "url": f"{base}/FountainPenManager_Setup_{APP_VERSION}.zip",
                "sha256": "PUT_SHA256_HERE",
            },
        },
    }


def sync_version_json(check: bool) -> bool:
    p = ROOT / "version.json"
    data = {}
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    expected = {"app": APP_NAME, "version": APP_VERSION}
    ok = data == expected
    if check or ok:
        return ok
    p.write_text(json.dumps(expected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


def sync_version_info(check: bool) -> bool:
    p = ROOT / "VERSION_INFO.txt"
    # Version, Datum UND Build-Tag werden aus app_info.py abgeleitet, damit der
    # Build-Tag bei einem Versionsbump nicht veraltet stehen bleibt.
    expected = (
        f"{APP_NAME} Version {APP_VERSION}\n"
        f"Datum: {APP_RELEASE_DATE}\n"
        f"Build: {APP_BUILD}\n"
    )
    current = p.read_text(encoding="utf-8") if p.exists() else ""
    ok = current == expected
    if check or ok:
        return ok
    p.write_text(expected, encoding="utf-8")
    return True


def sync_installer(check: bool) -> bool:
    p = ROOT / "installer" / "FountainPenManager_Setup.iss"
    if not p.exists():
        return True
    src = p.read_text(encoding="utf-8")
    new = re.sub(r'#define MyAppVersion "[^"]*"', f'#define MyAppVersion "{APP_VERSION}"', src)
    ok = new == src
    if check or ok:
        return ok
    p.write_text(new, encoding="utf-8")
    return True


def sync_latest_template(rel_path: str, check: bool) -> bool:
    p = ROOT / rel_path
    expected = _latest_template_data()
    try:
        current = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception:
        current = {}
    ok = current == expected
    if check or ok:
        return ok
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(expected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


def main() -> int:
    check = "--check" in sys.argv
    results = {
        "version.json": sync_version_json(check),
        "VERSION_INFO.txt": sync_version_info(check),
        "installer/FountainPenManager_Setup.iss": sync_installer(check),
        "latest.json.template": sync_latest_template("latest.json.template", check),
        "docs/latest.json.template": sync_latest_template("docs/latest.json.template", check),
    }
    if check:
        bad = [name for name, ok in results.items() if not ok]
        if bad:
            print(f"VERSION MISMATCH (Quelle app_info.py = {APP_VERSION}):")
            for name in bad:
                print(f"  - {name} ist nicht synchron")
            return 1
        print(f"Alle Versionsdateien synchron: {APP_VERSION}")
        return 0
    print(f"Versionen synchronisiert auf {APP_VERSION} ({APP_RELEASE_DATE})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
