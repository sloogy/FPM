#!/usr/bin/env python3
"""Namens-Audit über den Produktionscode (v0.3.04).

Zwei Prüfungen, die weder ``compileall`` (Syntax) noch ``tools/import_smoke``
(nur Modul-Toplevel) abdecken:

1. **Undefinierte Namen** (F821-artig, harter Fail): Ein Name wird gelesen,
   ist aber weder importiert noch definiert noch gebunden. Genau so entstand
   der v0.3.02-Split-Fehler (``SERVICE_HELP``/``QInputDialog`` in
   ``ui/pen_dialogs.py`` – NameError erst beim Öffnen des Dialogs).
2. **Ungenutzte Importe** (F401-artig, Ratchet): Obergrenze nur senkbar;
   bewusste Re-Exports werden mit ``# noqa`` in der Importzeile markiert.

Konservative Näherung (modulweiter Namensraum, keine Scope-Ketten): bindet
Funktions-/Lambda-/Comprehension-/with-/except-/for-Ziele, Walrus und
Klassennamen. Attributzugriffe (``self.x``) zählen nicht als Namen.
"""
from __future__ import annotations

import ast
import builtins
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ("database", "logic", "updater", "i18n", "ui")

# Ratchet: Ist-Stand nach der v0.3.04-Bereinigung (härtester Stand). Nur senken, nie erhöhen.
UNUSED_IMPORT_LIMIT = 0

BUILTIN = set(dir(builtins)) | {
    "__name__", "__file__", "__doc__", "__package__", "__spec__",
    "__loader__", "__builtins__", "__all__",
}


def _bind_args(args: ast.arguments, stores: set) -> None:
    for arg in [*args.posonlyargs, *args.args, *args.kwonlyargs,
                *([args.vararg] if args.vararg else []),
                *([args.kwarg] if args.kwarg else [])]:
        stores.add(arg.arg)


def audit_file(path: Path):
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    lines = src.splitlines()
    noqa_lines = {i + 1 for i, line in enumerate(lines) if "noqa" in line}

    imported: dict[str, int] = {}
    defined: set = set()
    used: set = set()
    stores: set = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                imported[(a.asname or a.name).split(".")[0]] = node.lineno
        elif isinstance(node, ast.ImportFrom):
            if node.module == "__future__":
                continue
            for a in node.names:
                imported[a.asname or a.name] = node.lineno
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defined.add(node.name)
            _bind_args(node.args, stores)
        elif isinstance(node, ast.Lambda):
            _bind_args(node.args, stores)
        elif isinstance(node, ast.ClassDef):
            defined.add(node.name)
        elif isinstance(node, ast.Name):
            (used if isinstance(node.ctx, ast.Load) else stores).add(node.id)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            stores.add(node.name)
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            stores.update(node.names)

    unused = sorted(
        name for name, lineno in imported.items()
        if name not in used and name != "*" and lineno not in noqa_lines
    )
    undefined = sorted(used - set(imported) - defined - stores - BUILTIN)
    return unused, undefined


def main() -> int:
    undefined_total: list[str] = []
    unused_total: list[str] = []
    for pkg in PACKAGES:
        for f in sorted((ROOT / pkg).rglob("*.py")):
            if "__pycache__" in f.parts:
                continue
            unused, undefined = audit_file(f)
            rel = f.relative_to(ROOT)
            undefined_total += [f"{rel}: {n}" for n in undefined]
            unused_total += [f"{rel}: {n}" for n in unused]

    ok = True
    if undefined_total:
        ok = False
        print(f"name audit: {len(undefined_total)} UNDEFINIERTE Namen (harter Fail):")
        for item in undefined_total:
            print(f"  F821 {item}")
    if len(unused_total) > UNUSED_IMPORT_LIMIT:
        ok = False
        print(f"name audit: {len(unused_total)} ungenutzte Importe "
              f"(Ratchet-Obergrenze: {UNUSED_IMPORT_LIMIT}):")
        for item in unused_total:
            print(f"  F401 {item}")
    if ok:
        print(f"name audit: OK (0 undefinierte Namen, "
              f"{len(unused_total)} ungenutzte Importe <= Limit {UNUSED_IMPORT_LIMIT})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
