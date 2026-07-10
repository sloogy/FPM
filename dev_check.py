"""Kleiner lokaler Check ohne App-Start: Syntax, lokale Imports und ZIP-Hygiene."""
from __future__ import annotations

import ast
import compileall
from pathlib import Path

ROOT = Path(__file__).resolve().parent

print("== Syntaxcheck ==")
ok = compileall.compile_dir(str(ROOT), quiet=1)
print("OK" if ok else "FEHLER")

print("\n== Lokale Importnamen ==")
files = list(ROOT.rglob("*.py"))
modules = {".".join(p.relative_to(ROOT).with_suffix("").parts): p for p in files}
errors = []
for p in files:
    try:
        tree = ast.parse(p.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        errors.append((str(p.relative_to(ROOT)), exc.lineno, "SyntaxError", exc.msg))
        continue
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            mod = node.module
            if not (mod == "app_info" or mod.startswith(("ui", "database", "logic", "i18n"))):
                continue
            target = modules.get(mod)
            if not target:
                errors.append((str(p.relative_to(ROOT)), node.lineno, "Modul fehlt", mod))
                continue
            target_tree = ast.parse(target.read_text(encoding="utf-8"))
            exported = set()
            for item in target_tree.body:
                if isinstance(item, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    exported.add(item.name)
                elif isinstance(item, (ast.Assign, ast.AnnAssign)):
                    targets = item.targets if isinstance(item, ast.Assign) else [item.target]
                    for tgt in targets:
                        if isinstance(tgt, ast.Name):
                            exported.add(tgt.id)
            for alias in node.names:
                if alias.name != "*" and alias.name not in exported:
                    errors.append((str(p.relative_to(ROOT)), node.lineno, "Name fehlt", f"{mod}.{alias.name}"))

if errors:
    for err in errors:
        print("FEHLER:", err)
else:
    print("OK")

print("\n== Pycache ==")
pycache = list(ROOT.rglob("__pycache__")) + list(ROOT.rglob("*.pyc"))
if pycache:
    for p in pycache:
        print("WARNUNG:", p.relative_to(ROOT))
else:
    print("OK")
