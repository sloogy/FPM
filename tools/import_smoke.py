#!/usr/bin/env python3
"""Import-Smoke über alle Produktionsmodule (v0.3.02).

Schließt die Lücke zwischen ``compileall`` (nur Syntax) und dem CI-GUI-Smoke
(braucht echtes Qt): Jedes Modul unter ui/, logic/, database/, updater/ und
i18n/ wird real importiert. Fehlen SQLAlchemy/PySide6 (Sandbox), werden die
bedingten Stubs aus ``tests/_stub_env.py`` aktiviert; in der CI laufen die
Importe gegen die echten Pakete.

Genau diese Prüfung hätte den v0.3.01-Importfehler
(`from database.repositories import PenRepository, _data_dir`) sofort
gefangen – compileall und die ohnehin an Qt scheiternden GUI-Tests taten es
nicht. Exit 0 = alle Importe sauber, Exit 1 = Fehlerliste.
"""
from __future__ import annotations

import importlib
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests._stub_env import install_pyside6_stub, install_sqlalchemy_stub  # noqa: E402

PACKAGES = ("database", "logic", "updater", "i18n", "ui")
SKIP = {
    # Skripte mit Seiteneffekten beim Import (argparse/main-Ausführung):
    "updater.check_update", "updater.apply_update", "updater.generate_manifest",
    "updater.startup_check",
}


def module_names() -> list[str]:
    names: list[str] = []
    for pkg in PACKAGES:
        for f in sorted((ROOT / pkg).rglob("*.py")):
            if "__pycache__" in f.parts:
                continue
            rel = f.relative_to(ROOT).with_suffix("")
            name = ".".join(rel.parts)
            if name.endswith(".__init__"):
                name = name[: -len(".__init__")]
            if name in SKIP:
                continue
            names.append(name)
    return names


def main() -> int:
    sa_stub = install_sqlalchemy_stub()
    qt_stub = install_pyside6_stub()
    failures: list[tuple[str, str]] = []
    for name in module_names():
        try:
            importlib.import_module(name)
        except Exception:  # noqa: BLE001 - Sammelbericht gewollt
            failures.append((name, traceback.format_exc(limit=3)))
    mode = []
    mode.append("sqlalchemy=STUB" if sa_stub else "sqlalchemy=echt")
    mode.append("PySide6=STUB" if qt_stub else "PySide6=echt")
    if failures:
        print(f"import smoke: {len(failures)} Modul(e) nicht importierbar ({', '.join(mode)})")
        for name, tb in failures:
            print(f"--- {name} ---")
            print(tb)
        return 1
    print(f"import smoke: OK ({len(module_names())} Module importierbar; {', '.join(mode)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
