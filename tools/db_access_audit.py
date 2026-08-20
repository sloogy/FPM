#!/usr/bin/env python3
"""DB-Zugriffs-Ratchet für UI-Dateien (Enterprise-Audit v0.3.00, P1).

Zählt direkte ``session.query(``-Aufrufe in ``ui/`` und erzwingt eine
Obergrenze pro Gesamtbestand sowie eine Datei-Positivliste des Ist-Zustands.
Neue direkte Queries in bislang sauberen Dateien schlagen sofort fehl;
die Gesamtgrenze wird mit jeder Migrationsrunde in Richtung Service-/
Repository-Schicht manuell gesenkt.

v0.3.01-Basismessung nach Umbau:
- dashboard_widget: 0 (vorher 8) – vollständig über Service/Repos
- pen_widget/ink_widget: Haupttabellen über Repositories
Exit 0 = innerhalb der Grenzen, Exit 1 = Verstoß.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Ratchet-Obergrenzen (nur senken, nie erhöhen):
TOTAL_UI_QUERY_LIMIT = 49  # v0.3.02: PenWidget/Dialoge + InkWidget query-frei
# Dateien, die bereits vollständig query-frei sind und es bleiben müssen:
QUERY_FREE_UI_FILES = (
    "dashboard_widget.py",
    "pen_widget.py",      # v0.3.02: Repository-/Service-Schicht
    "pen_dialogs.py",     # v0.3.02: ausgelagerte Füller-Dialoge
    "ink_widget.py",      # v0.3.02
)


def scan() -> tuple[int, dict[str, int]]:
    per_file: dict[str, int] = {}
    for f in sorted((ROOT / "ui").glob("*.py")):
        n = f.read_text(encoding="utf-8", errors="replace").count("session.query(")
        if n:
            per_file[f.name] = n
    return sum(per_file.values()), per_file


def main() -> int:
    total, per_file = scan()
    ok = True
    for name in QUERY_FREE_UI_FILES:
        if per_file.get(name):
            ok = False
            print(f"db access audit: {name} enthält wieder {per_file[name]} direkte Queries (muss 0 bleiben)")
    if total > TOTAL_UI_QUERY_LIMIT:
        ok = False
        print(f"db access audit: {total} direkte UI-Queries (Ratchet-Obergrenze: {TOTAL_UI_QUERY_LIMIT})")
        for name, n in sorted(per_file.items(), key=lambda x: -x[1]):
            print(f"  - {name}: {n}")
    if ok:
        print(
            f"db access audit: OK ({total} direkte UI-Queries <= Limit {TOTAL_UI_QUERY_LIMIT}; "
            f"{len(QUERY_FREE_UI_FILES)} Datei(en) dauerhaft query-frei)"
        )
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
