#!/usr/bin/env python3
"""Generate and validate platform-specific, hash-locked dependencies.

Official builds require both ``constraints-linux.lock`` and
``constraints-windows.lock``. Generation uses ``uv pip compile`` because it can
resolve target platforms without executing target wheels. Missing or malformed
locks always fail ``--check``; there is no release fallback to unpinned inputs.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQ_FILES = ("requirements.txt", "requirements-build.txt")
PLATFORMS = {
    "linux": "x86_64-unknown-linux-gnu",
    "windows": "x86_64-pc-windows-msvc",
}
_NAME = re.compile(r"^\s*([A-Za-z0-9_.-]+)")
_LOCK_ENTRY = re.compile(
    r"^(?P<name>[A-Za-z0-9_.-]+)==(?P<version>[^\s;]+)(?:\s*;[^\\]+)?(?P<rest>.*)$",
    re.S,
)
_HASH = re.compile(r"--hash=sha256:[0-9a-f]{64}\b")


def lock_path(platform_name: str) -> Path:
    return ROOT / f"constraints-{platform_name}.lock"


def direct_requirements() -> list[str]:
    names: set[str] = set()
    for rel in REQ_FILES:
        for line in (ROOT / rel).read_text(encoding="utf-8").splitlines():
            line = line.split("#", 1)[0].strip()
            if not line or line.startswith(("-", "http://", "https://")):
                continue
            match = _NAME.match(line)
            if match:
                names.add(match.group(1).lower().replace("_", "-"))
    return sorted(names)


def _logical_entries(text: str) -> list[str]:
    entries: list[str] = []
    current = ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if current:
            current += " " + line
        else:
            current = line
        if current.endswith("\\"):
            current = current[:-1].rstrip()
            continue
        entries.append(current)
        current = ""
    if current:
        entries.append(current)
    return entries


def check_platform(platform_name: str) -> list[str]:
    path = lock_path(platform_name)
    if not path.is_file():
        return [f"{path.name} fehlt"]
    text = path.read_text(encoding="utf-8")
    if f"--platform {platform_name}" not in text:
        return [f"{path.name}: Generator-/Plattform-Header fehlt"]

    locked: set[str] = set()
    errors: list[str] = []
    for index, entry in enumerate(_logical_entries(text), 1):
        match = _LOCK_ENTRY.match(entry)
        if not match:
            errors.append(f"{path.name}: Eintrag {index} ist nicht exakt name==version")
            continue
        if not _HASH.search(entry):
            errors.append(f"{path.name}: {match.group('name')} hat keinen sha256-Hash")
        locked.add(match.group("name").lower().replace("_", "-"))
    for name in direct_requirements():
        if name not in locked:
            errors.append(f"{path.name}: Direktabhängigkeit fehlt: {name}")
    return errors


def check(platform_name: str) -> int:
    targets = PLATFORMS if platform_name == "all" else {platform_name: PLATFORMS[platform_name]}
    errors: list[str] = []
    for name in targets:
        errors.extend(check_platform(name))
    if errors:
        for error in errors:
            print(f"dependency lock: {error}")
        return 1
    print("dependency lock: OK (plattformgetrennt, exakt und hash-gelockt)")
    return 0


def generate_one(platform_name: str) -> int:
    uv = shutil.which("uv")
    if not uv:
        print("dependency lock: 'uv' fehlt. Installiere uv oder nutze den GitHub-Workflow.")
        return 2
    target = PLATFORMS[platform_name]
    command = [
        uv,
        "pip",
        "compile",
        *REQ_FILES,
        "--python-version",
        "3.12",
        "--python-platform",
        target,
        "--generate-hashes",
        "--no-annotate",
        "--no-python-downloads",
        "--custom-compile-command",
        f"python tools/gen_lockfile.py --platform {platform_name}",
        "--output-file",
        str(lock_path(platform_name)),
    ]
    print("dependency lock:", " ".join(command))
    return subprocess.run(command, cwd=ROOT, check=False).returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--platform", choices=["linux", "windows", "all"], default="all")
    args = parser.parse_args()
    if args.check:
        return check(args.platform)
    targets = list(PLATFORMS) if args.platform == "all" else [args.platform]
    for target in targets:
        code = generate_one(target)
        if code:
            return code
    return check(args.platform)


if __name__ == "__main__":
    raise SystemExit(main())
