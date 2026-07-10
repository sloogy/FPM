#!/usr/bin/env python3
"""Translation quality audit for FountainPen Manager.

Checks three distinct failure modes that the structural audits miss:

  1. UNTRANSLATED  – EN or FR value is identical to DE but is not a
                     language-neutral term (tech jargon, proper nouns,
                     numeric codes, known intentional same-language strings).

  2. LEAKAGE       – EN/FR value differs from DE but still contains German
                     words or characters (partial / word-salad translations).

  3. TERNARY       – Ternary-expression string literals in Qt text calls
                     that are not routed through t().  The main key-wiring
                     audit misses these because its AST walk does not
                     descend into IfExp nodes.

Exit code 0 = all checks pass.  Non-zero = at least one failure.
"""
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI_FILES = sorted((ROOT / "ui").glob("*.py"))

# ── helpers ──────────────────────────────────────────────────────
def load(lang: str) -> dict:
    return json.loads((ROOT / "i18n" / f"{lang}.json").read_text())

# Terms that are legitimately identical across DE / EN / FR
NEUTRAL = re.compile(
    r"^(Status|Dashboard|OK|EDC|CSV|PDF|JSON|SQLite|Markdown|Shimmer|Shading|Sheen|"
    r"Feathering|Eyedropper|Feed|Nibmeister|Import|Export|Converter|Shop|Wishlist|"
    r"Score|Total|Backup|Navigation|Rotation|Pigment|Material|Normal|Kompakt|Service|"
    r"Full Auto.*|Auto Mode|Expert Mode.*|Easy Mode.*|Glossary|Glossar|Glossaire|"
    r"Info|Auto|Version.*|Python.*|PySide6.*|SQLAlchemy.*|g/m.*|<hr>|#[0-9A-Fa-f]+|"
    r"z\.B\.|p\.ex\.|e\.g\.|[A-Z]{2,4}\b.*|[0-9].*|\{.*\}|\*\.|"
    r"🇩🇪.*|🇬🇧.*|🇫🇷.*|Deutsch|English|Français|EF|F\b|M\b|B\b|BB\b|"
    r"Prio|Priority|Priorité)",
    re.I,
)

GERMAN_LEAK = re.compile(
    r"[äöüÄÖÜß]|"
    r"(?<!\w)("
    r"mit|und|oder|für|nach|nicht|wird|wurde|beim|mehr|langer|"
    r"Tage|Füller|Tinten?|Federn?|Feder|Eingefüllt|Zeigt|Noch|"
    r"Wähle|Bitte|Klicke|Neue[rs]?|Keine[rs]?|Beim|Beim|"
    r"angelegt|gespeichert|gesperrt|bearbeiten|hinzufügen|erfassen|"
    r"übernehmen|zurücksetzen|speichern|löschen|entsperren|wechseln|"
    r"schaltbar|aktiviert|deaktiviert|einschalten|ausschalten"
    r")(?!\w)",
    re.I,
)

VISIBLE_METHODS = {
    "setWindowTitle", "setText", "setTitle", "setPlaceholderText", "setToolTip",
    "addRow", "addItem", "addTab", "addAction",
    "setHorizontalHeaderLabels", "setVerticalHeaderLabels",
    "information", "warning", "critical", "question", "getText", "getItem",
}
VISIBLE_CONSTRUCTORS = {
    "QLabel", "QPushButton", "QGroupBox", "QRadioButton", "QCheckBox",
    "QAction", "QTableWidgetItem", "QListWidgetItem",
}
DE_WORD = re.compile(
    r"[äöüÄÖÜß]|(?<!\w)("
    r"Füller|Tinten?|Federn?|Papier|Ausgaben?|Einstellungen?|Regeln?|Hilfe|"
    r"Suchen|Hinzufügen|Löschen|Bearbeiten|Speichern|Abbrechen|Schließen|"
    r"Auswahl|Wähle|Klicke|Bitte|Noch keine|Keine[rs]?"
    r")(?!\w)",
    re.I,
)


# Values legitimately identical across all three languages
KNOWN_IDENTICAL_OK = {
    "🏠  Dashboard",   # Dashboard is an international term
    "⬆ Import",        # tech verb, universally understood
    "⬇ Export",        # tech verb
    "🧾  Wishlist",    # anglicism in widespread use
    "Full Auto",
    "Easy Mode",
    "Expert Mode",
    "Auto Mode",
}

# ── check 1 + 2: JSON translation quality ────────────────────────
def check_json_quality(de: dict, en: dict, fr: dict) -> list[str]:
    errors: list[str] = []
    ui_de = de.get("ui", {})
    ui_en = en.get("ui", {})
    ui_fr = fr.get("ui", {})

    for sec, sec_dict in ui_de.items():
        if not isinstance(sec_dict, dict):
            continue
        for k, dv in sec_dict.items():
            if not isinstance(dv, str) or len(dv) <= 2:
                continue
            ev = ui_en.get(sec, {}).get(k, "")
            fv = ui_fr.get(sec, {}).get(k, "")
            key = f"ui.{sec}.{k}"

            for lang, val in (("EN", ev), ("FR", fv)):
                if val == dv and not NEUTRAL.match(dv.strip()) and dv not in KNOWN_IDENTICAL_OK:
                    errors.append(
                        f"UNTRANSLATED  [{lang}] {key}\n"
                        f"              DE = {dv[:70]!r}"
                    )
                elif val != dv and GERMAN_LEAK.search(val):
                    errors.append(
                        f"LEAKAGE       [{lang}] {key}\n"
                        f"              DE = {dv[:60]!r}\n"
                        f"              {lang} = {val[:60]!r}"
                    )
    return errors


# ── check 3: ternary literals in Qt text calls ───────────────────
class TernaryLiteralVisitor(ast.NodeVisitor):
    def __init__(self, source: str):
        self.source = source
        self.hits: list[tuple[int, str]] = []

    def _is_t_call(self, node: ast.expr) -> bool:
        """Returns True if node is a t("...") / t('...') call."""
        return (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "t"
        )

    def _contains_german(self, node: ast.expr) -> bool:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return bool(DE_WORD.search(node.value))
        if isinstance(node, ast.JoinedStr):  # f-string
            for v in node.values:
                if isinstance(v, ast.Constant) and isinstance(v.value, str):
                    if DE_WORD.search(v.value):
                        return True
        return False

    def _check_call_arg(self, node: ast.expr, lineno: int, context: str):
        # The argument itself is a German constant
        if self._contains_german(node) and not self._is_t_call(node):
            self.hits.append((lineno, f"{context}: {ast.unparse(node)[:80]}"))
            return
        # Ternary: arg is `"a" if cond else "b"` where either branch is German
        if isinstance(node, ast.IfExp):
            for branch in (node.body, node.orelse):
                if self._contains_german(branch) and not self._is_t_call(branch):
                    self.hits.append(
                        (lineno, f"{context} [ternary]: {ast.unparse(node)[:80]}")
                    )
                    break

    def visit_Call(self, node: ast.Call):
        func = node.func
        name = None
        if isinstance(func, ast.Name):
            name = func.id
        elif isinstance(func, ast.Attribute):
            name = func.attr

        if name in VISIBLE_METHODS:
            for arg in node.args:
                self._check_call_arg(arg, node.lineno, name)
        elif name in VISIBLE_CONSTRUCTORS:
            if node.args:
                self._check_call_arg(node.args[0], node.lineno, name)

        self.generic_visit(node)


def check_ternary_literals(files: list[Path]) -> list[str]:
    errors: list[str] = []
    for f in files:
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        v = TernaryLiteralVisitor(f.read_text(encoding="utf-8"))
        v.visit(tree)
        for lineno, desc in v.hits:
            errors.append(f"TERNARY_LITERAL  {f.name}:{lineno}  {desc}")
    return errors


# ── main ─────────────────────────────────────────────────────────
def main() -> int:
    de, en, fr = load("de"), load("en"), load("fr")

    json_errors   = check_json_quality(de, en, fr)
    ternary_errors = check_ternary_literals(UI_FILES)

    all_errors = json_errors + ternary_errors
    if all_errors:
        print(f"i18n quality audit: FAIL ({len(all_errors)} issue(s))")
        for e in all_errors:
            print(f"  {e}")
        return 1
    else:
        print(
            f"i18n quality audit: OK  "
            f"(0 untranslated, 0 leakage, 0 ternary literals)"
        )
        return 0


if __name__ == "__main__":
    sys.exit(main())
