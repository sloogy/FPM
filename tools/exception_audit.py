#!/usr/bin/env python3
"""Exception-Ratchet (Enterprise-Audit v0.3.00, P2).

Zählt breite Handler im Produktionscode und erzwingt zwei Regeln:
1. Nackte ``except:``-Klauseln sind verboten (0 erlaubt).
2. ``except Exception`` darf die festgeschriebene Obergrenze nicht
   überschreiten. Die Grenze wird bei jeder Präzisierungsrunde manuell
   GESENKT, nie erhöht (Ratchet-Prinzip) – so wird der Bestand von
   134+ Handlern schrittweise und messbar abgebaut, ohne einen riskanten
   Big-Bang-Umbau zu erzwingen.

Exit 0 = innerhalb der Grenzen, Exit 1 = Verstoß.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ("ui", "logic", "database", "updater", "i18n")
EXTRA_FILES = ("main.py", "app_info.py")

# Ratchet-Obergrenze. Historie:
#   v0.3.00-Audit: 134 gemeldet (Produktionsdateien), Messung dieses Tools: s.u.
#   v0.3.01: Baseline nach Dashboard-/Service-Umbau festgeschrieben.
BROAD_EXCEPTION_LIMIT = 146
BARE_EXCEPT_LIMIT = 0

_BROAD = re.compile(r"^\s*except\s+Exception\b")
_BARE = re.compile(r"^\s*except\s*:")


def scan() -> tuple[int, int, list[str]]:
    broad = 0
    bare = 0
    bare_hits: list[str] = []
    files: list[Path] = []
    for pkg in PACKAGES:
        files.extend(sorted((ROOT / pkg).rglob("*.py")))
    files.extend(ROOT / f for f in EXTRA_FILES)
    for f in files:
        if "__pycache__" in f.parts or not f.exists():
            continue
        for lineno, line in enumerate(
            f.read_text(encoding="utf-8", errors="replace").splitlines(), 1
        ):
            if _BARE.match(line):
                bare += 1
                bare_hits.append(f"{f.relative_to(ROOT)}:{lineno}")
            elif _BROAD.match(line):
                broad += 1
    return broad, bare, bare_hits


def main() -> int:
    broad, bare, bare_hits = scan()
    ok = True
    if bare > BARE_EXCEPT_LIMIT:
        ok = False
        print(f"exception audit: {bare} nackte 'except:'-Klauseln (erlaubt: {BARE_EXCEPT_LIMIT})")
        for hit in bare_hits:
            print(f"  - {hit}")
    if broad > BROAD_EXCEPTION_LIMIT:
        ok = False
        print(
            f"exception audit: {broad} breite 'except Exception' "
            f"(Ratchet-Obergrenze: {BROAD_EXCEPTION_LIMIT})"
        )
    if ok:
        print(
            f"exception audit: OK ({broad} breite Handler <= Limit {BROAD_EXCEPTION_LIMIT}, "
            f"{bare} nackte except)"
        )
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
