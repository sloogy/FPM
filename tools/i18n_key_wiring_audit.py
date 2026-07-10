#!/usr/bin/env python3
"""Audit that visible Qt string literals are wired through translation keys.

This is stricter than the runtime bridge audit: it checks the source code for
likely visible German strings in common Qt text constructors/methods and fails
when such strings are still passed directly instead of via t("...").
"""
from __future__ import annotations

import ast
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
FILES = [*sorted((ROOT / "ui").glob("*.py")), ROOT / "main.py"]
VISIBLE_CALLS = {
    "QLabel", "QPushButton", "QGroupBox", "QRadioButton", "QCheckBox",
    "QAction", "QMenu", "QTableWidgetItem", "QListWidgetItem",
}
VISIBLE_HELPERS = {"_card", "_summary_card", "row", "_note", "_styled_button", "_new_page", "_v_card", "_form_card"}
VISIBLE_METHODS = {
    "setWindowTitle", "setText", "setSpecialValueText", "setTitle", "setPlaceholderText", "setToolTip",
    "addAction", "addMenu", "addItem", "addItems", "addRow", "addTab",
    "setHorizontalHeaderLabels", "setVerticalHeaderLabels", "information", "warning",
    "critical", "question", "getText", "getItem", "getOpenFileName",
    "getSaveFileName", "getExistingDirectory",
}
SOURCE_GERMAN_TERMS = re.compile(
    r"(Füller|Tinte|Tinten|Feder|Federn|Papier|Ausgaben|Einstellungen|Regeln|Hilfe|"
    r"Suchen|Suche|Hinzufügen|hinzufügen|Löschen|löschen|Bearbeiten|Speichern|"
    r"Übernehmen|Einfüllen|Gereinigt|Datenbank|Pfad|Durchsuchen|Währung|Region|"
    r"Sprache|Darstellung|Allgemein|Warnung|Fehler|Hinweis|Bitte|Kein|Keine|"
    r"Tage|Reinigung|Sperren|Überfällig|Aktuelle|Letzte|Vorhandene|Neue|"
    r"Größe|Größenvergleich|Kaufpreis|Kaufdatum|Händler|Beschreibung|Kategorie|"
    r"Öffnen|öffnen|Schließen|schließen|Abbrechen|Fortfahren|Zurücksetzen|"
    r"Archiviert|Archivieren|Archiv|Aktiv|Einsatz|Thema|Limit|abgeschlossen|geschlossen|InkLoad|Sammlungswert|Gesamt|GESAMT|Rest|REST|leer|Leer|gekauft|geplant|vorhanden|auswählen)"
)
SKIP_PREFIXES = ("ui.", "QWidget", "QFrame", "QMainWindow", "#", "/*")


def _func_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _strings_from(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.JoinedStr):
        return ["".join(part.value if isinstance(part, ast.Constant) and isinstance(part.value, str) else "{}" for part in node.values)]
    if isinstance(node, (ast.List, ast.Tuple)):
        out: list[str] = []
        for elt in node.elts:
            out.extend(_strings_from(elt))
        return out
    return []


def _is_candidate(text: str) -> bool:
    s = text.strip()
    if not s or len(s) > 800 or s.startswith(SKIP_PREFIXES):
        return False
    if re.fullmatch(r"[\d\s.,'/:+\-–—|()%#×✓✕✅❌⚠ℹ⭐💍]+", s):
        return False
    return bool(SOURCE_GERMAN_TERMS.search(s))



def _audit_no_global_show_hook(errors: list[str]) -> None:
    qt_path = ROOT / "i18n" / "qt_i18n.py"
    text = qt_path.read_text(encoding="utf-8")
    forbidden = [
        "QWidget.show =",
        "_orig_show = QWidget.show",
        "def _show(self",
        "_fpm_i18n_combo_items",
    ]
    for needle in forbidden:
        if needle in text:
            errors.append(f"i18n/qt_i18n.py: forbidden runtime/performance pattern remains: {needle}")


def _audit_main_window_no_refresh_walk(errors: list[str]) -> None:
    path = ROOT / "ui" / "main_window.py"
    text = path.read_text(encoding="utf-8")
    if "apply_widget_tree(widget)" in text or "apply_widget_tree(self)" in text:
        errors.append("ui/main_window.py: main navigation/refresh must not recursively walk widget trees for i18n")

def main() -> int:
    errors: list[str] = []
    _audit_no_global_show_hook(errors)
    _audit_main_window_no_refresh_walk(errors)
    for path in FILES:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"{path.relative_to(ROOT)}: parse failed: {exc}")
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = _func_name(node.func)
            if name not in VISIBLE_CALLS and name not in VISIBLE_METHODS and name not in VISIBLE_HELPERS:
                continue
            for arg in node.args:
                for text in _strings_from(arg):
                    if _is_candidate(text):
                        errors.append(f"{path.relative_to(ROOT)}:{getattr(node, 'lineno', 0)} direct visible German literal: {text!r}")
    if errors:
        print("i18n key wiring audit: FEHLER")
        for err in errors[:80]:
            print("  -", err)
        if len(errors) > 80:
            print(f"  ... {len(errors) - 80} more")
        return 1
    print("i18n key wiring audit: OK (0 direct visible German literals in Qt text calls)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
