#!/usr/bin/env python3
"""Derive all current release names from the single app version source."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app_info import APP_NAME, APP_VERSION  # noqa: E402
from tools.build_lifeplanner_module import module_asset_name  # noqa: E402


def classify_tag(tag: str) -> str:
    """Classify an exact production tag or numbered release-candidate tag."""
    release_tag = f"v{APP_VERSION}"
    if tag == release_tag:
        return "production"
    if re.fullmatch(rf"{re.escape(release_tag)}-rc\.[1-9][0-9]*", tag):
        return "release-candidate"
    raise ValueError(
        f"tag {tag!r} does not match {release_tag!r} or "
        f"{release_tag + '-rc.N'!r}"
    )


def metadata() -> dict[str, str]:
    manifest = json.loads((ROOT / "module.json").read_text(encoding="utf-8"))
    if manifest.get("version") != APP_VERSION:
        raise ValueError(
            f"module.json version mismatch: {manifest.get('version')} != {APP_VERSION}; run tools/sync_version.py"
        )
    tag = f"v{APP_VERSION}"
    module_id = manifest["id"]
    return {
        "app_name": APP_NAME,
        "app_version": APP_VERSION,
        "release_tag": tag,
        "windows_portable": f"FountainPenManager-v{APP_VERSION}-portable-windows.zip",
        "linux_portable": f"FountainPenManager-v{APP_VERSION}-portable-linux.zip",
        "windows_installer": f"FountainPenManager_Setup_{APP_VERSION}.exe",
        "windows_installer_zip": f"FountainPenManager_Setup_{APP_VERSION}.zip",
        "module_windows": module_asset_name(module_id, APP_VERSION, "windows-x86_64"),
        "module_linux": module_asset_name(module_id, APP_VERSION, "linux-x86_64"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--github-env", type=Path)
    parser.add_argument("--validate-tag")
    args = parser.parse_args()
    try:
        data = metadata()
        if args.validate_tag:
            release_kind = classify_tag(args.validate_tag)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"release metadata: {exc}", file=sys.stderr)
        return 2
    if args.validate_tag:
        print(f"release tag: OK ({release_kind})")
        return 0
    if args.github_env:
        mapping = {
            "FPM_APP_VERSION": data["app_version"],
            "FPM_RELEASE_TAG": data["release_tag"],
            "FPM_WINDOWS_PORTABLE": data["windows_portable"],
            "FPM_LINUX_PORTABLE": data["linux_portable"],
            "FPM_WINDOWS_INSTALLER": data["windows_installer"],
            "FPM_WINDOWS_INSTALLER_ZIP": data["windows_installer_zip"],
            "FPM_MODULE_WINDOWS": data["module_windows"],
            "FPM_MODULE_LINUX": data["module_linux"],
        }
        args.github_env.parent.mkdir(parents=True, exist_ok=True)
        with args.github_env.open("a", encoding="utf-8") as handle:
            for key, value in mapping.items():
                handle.write(f"{key}={value}\n")
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
