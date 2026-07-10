#!/usr/bin/env python3
"""Audit der i18n-Dateien.

Prüft, ob alle Sprachdateien dieselbe Key-Struktur wie de.json haben,
ob Werte leer sind und ob ungültige JSON-Dateien vorliegen.
Exitcode 0 = sauber, Exitcode 1 = Fehler gefunden.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
I18N = ROOT / "i18n"
BASE_LANG = "de"
LANGS = ("de", "en", "fr")


def load(lang: str) -> dict[str, Any]:
    path = I18N / f"{lang}.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"{path}: {exc}") from exc


def flatten(data: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in data.items():
        full = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            out.update(flatten(value, full))
        else:
            out[full] = value
    return out


def main() -> int:
    errors: list[str] = []
    base = flatten(load(BASE_LANG))
    base_keys = set(base)

    for lang in LANGS:
        flat = flatten(load(lang))
        keys = set(flat)
        missing = sorted(base_keys - keys)
        extra = sorted(keys - base_keys)
        empty = sorted(k for k, v in flat.items() if isinstance(v, str) and v == "")

        if missing:
            errors.append(f"{lang}: fehlende Keys: " + ", ".join(missing))
        if extra:
            errors.append(f"{lang}: überzählige Keys: " + ", ".join(extra))
        if empty:
            errors.append(f"{lang}: leere Übersetzungen: " + ", ".join(empty))

    if errors:
        print("i18n audit: FEHLER")
        for err in errors:
            print("-", err)
        return 1

    print(f"i18n audit: OK ({len(base_keys)} Keys × {len(LANGS)} Sprachen)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
