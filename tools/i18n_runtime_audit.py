#!/usr/bin/env python3
"""Static audit for legacy German UI strings.

The original i18n audit only checks JSON key parity.  This audit checks the
runtime bridge too: likely visible Qt strings extracted from ui/*.py and main.py
must translate away from German for English and French.

It deliberately avoids requiring PySide6, so it can run in CI without a GUI.
"""
from __future__ import annotations

import ast
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from i18n.translator import Translator  # noqa: E402
from i18n.qt_i18n import translate_source_text  # noqa: E402

FILES = [*sorted((ROOT / "ui").glob("*.py")), ROOT / "main.py"]
VISIBLE_CALLS = {
    "QLabel", "QPushButton", "QGroupBox", "QRadioButton", "QCheckBox",
    "QAction", "QTableWidgetItem", "QListWidgetItem",
}
VISIBLE_HELPERS = {"_card", "_summary_card", "row", "_note", "_styled_button", "_new_page", "_v_card", "_form_card"}
VISIBLE_METHODS = {
    "setWindowTitle", "setText", "setSpecialValueText", "setPlaceholderText", "addAction", "addItem",
    "addRow", "setHorizontalHeaderLabels", "setVerticalHeaderLabels",
    "information", "warning", "critical", "question", "getText", "getItem",
    "getInt", "getDouble", "getOpenFileName", "getSaveFileName",
    "getExistingDirectory",
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
SKIP_PREFIXES = ("QWidget", "QFrame", "QMainWindow", "#", "/*")


def _func_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _strings_from(node: ast.AST) -> list[str]:
    out: list[str] = []
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        out.append(node.value)
    elif isinstance(node, ast.JoinedStr):
        # Keep literal parts of f-strings.  Placeholders are user/data values and
        # should not be translated by this static audit.
        text = "".join(part.value if isinstance(part, ast.Constant) and isinstance(part.value, str) else "{}" for part in node.values)
        out.append(text)
    elif isinstance(node, (ast.List, ast.Tuple)):
        for elt in node.elts:
            out.extend(_strings_from(elt))
    return out


def _is_candidate(text: str) -> bool:
    s = text.strip()
    if not s or len(s) > 600:
        return False
    if s.startswith(SKIP_PREFIXES):
        return False
    if "{" in s and "}" in s and "{}" not in s:
        return False
    if re.fullmatch(r"[\d\s.,'/:+\-–—|()%#×✓✕✅❌⚠ℹ⭐💍]+", s):
        return False
    return bool(SOURCE_GERMAN_TERMS.search(s))


def extract_candidates() -> dict[str, set[tuple[str, int]]]:
    candidates: dict[str, set[tuple[str, int]]] = {}
    for path in FILES:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = _func_name(node.func)
            if name not in VISIBLE_CALLS and name not in VISIBLE_METHODS and name not in VISIBLE_HELPERS:
                continue
            args = list(node.args)
            # For addRow(label, widget) the first argument is a label.  For
            # QMessageBox parent,title,text the first argument is parent; string
            # extraction still catches title/text.
            for arg in args:
                for text in _strings_from(arg):
                    if _is_candidate(text):
                        candidates.setdefault(text, set()).add((str(path.relative_to(ROOT)), getattr(node, "lineno", 0)))
    return candidates


def main() -> int:
    tr = Translator.instance()
    candidates = extract_candidates()
    errors: list[str] = []
    for lang in ("en", "fr"):
        tr.set_language(lang)
        bad: list[str] = []
        # Some words are legitimate in target languages too: “Region” is English,
        # “Papier” is French.  Source detection stays stricter than target detection.
        target_terms = SOURCE_GERMAN_TERMS
        if lang == "en":
            target_terms = re.compile(SOURCE_GERMAN_TERMS.pattern.replace("|Region", ""))
        elif lang == "fr":
            target_terms = re.compile(SOURCE_GERMAN_TERMS.pattern.replace("|Papier", ""))
        for source in sorted(candidates):
            translated = translate_source_text(source, lang)
            if translated == source or target_terms.search(translated):
                locs = ", ".join(f"{p}:{ln}" for p, ln in sorted(candidates[source])[:3])
                bad.append(f"{source!r} -> {translated!r} ({locs})")
        if bad:
            errors.append(f"{lang}: {len(bad)} likely visible strings still German")
            errors.extend("  - " + item for item in bad[:40])
            if len(bad) > 40:
                errors.append(f"  ... {len(bad) - 40} more")

    if errors:
        print("i18n runtime audit: FEHLER")
        for err in errors:
            print(err)
        return 1
    print(f"i18n runtime audit: OK ({len(candidates)} likely visible German UI strings covered for EN/FR)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
