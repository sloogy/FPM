#!/usr/bin/env python3
"""Fail if tracked paths are invalid or hazardous on Windows."""
from __future__ import annotations
import os
import subprocess
from pathlib import Path, PurePosixPath

INVALID_CHARS = set('<>:"\\|?*')
RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


def tracked_paths() -> list[str]:
    try:
        out = subprocess.check_output(
            ["git", "ls-files", "-z"], stderr=subprocess.DEVNULL
        )
        return [
            x.decode("utf-8", "surrogateescape")
            for x in out.split(b"\0")
            if x
        ]
    except (FileNotFoundError, subprocess.CalledProcessError):
        root = Path(__file__).resolve().parents[1]
        ignored = {
            ".git",
            ".venv",
            "venv",
            "build",
            "dist",
            "release",
            "__pycache__",
            ".pytest_cache",
        }
        paths: list[str] = []
        for current, dirnames, filenames in os.walk(root):
            # Prune generated trees before descending into them. This keeps the
            # source-ZIP fallback fast even after a large PyInstaller build.
            dirnames[:] = [name for name in dirnames if name not in ignored]
            current_path = Path(current)
            for filename in filenames:
                paths.append((current_path / filename).relative_to(root).as_posix())
        return paths


def problems(path: str) -> list[str]:
    issues: list[str] = []
    for part in PurePosixPath(path).parts:
        if part.endswith((" ", ".")):
            issues.append("Komponente endet mit Leerzeichen/Punkt")
        if any(ord(ch) < 32 for ch in part):
            issues.append("ASCII-Steuerzeichen")
        if any(ch in INVALID_CHARS for ch in part):
            issues.append("Windows-unzulässiges Zeichen")
        stem = part.split(".", 1)[0].upper()
        if stem in RESERVED:
            issues.append("reservierter Windows-Gerätename")
    return issues


def main() -> int:
    bad = [(p, problems(p)) for p in tracked_paths() if problems(p)]
    if bad:
        print("Windows-ungültige Git-Pfade:")
        for path, issues in bad:
            print(f"  {path!r}: {', '.join(sorted(set(issues)))}")
        return 1
    print("OK: keine Windows-ungültigen versionierten Pfade")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
