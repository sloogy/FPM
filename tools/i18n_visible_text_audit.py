#!/usr/bin/env python3
"""i18n Visible-Text-Audit: führt die ECHTE Übersetzungsfunktion aus.

Hintergrund
-----------
Die statischen Audits (i18n_audit, i18n_quality_audit, i18n_key_wiring_audit)
prüfen JSON-Paritäten und t("key")-Verdrahtung. Der i18n_runtime_audit prüft
sichtbare Literale gegen translate_source_text(), erkennt Kandidaten aber nur
über eine CASE-SENSITIVE Keyword-Liste — genau die Fehlerklasse (ALL-CAPS-
Labels wie "FÜLLER AKTIV"), die im v0.2.50-Release-Report zwei falsche
Aussagen verursacht hat, würde dadurch erneut durchrutschen.

Dieses Audit ist die strikte Obermenge:

1. Kandidaten = String-Literale an Qt-Sinks, in Custom-Helpern UND in
   translate_source_text(...)-Aufrufen (ui/ + logic/ + main.py).
2. Deutsch-Erkennung case-INSENSITIVE: Umlaute/ß ODER Keyword-Liste.
3. Jeder Kandidat wird durch das echte translate_source_text() für EN und FR
   geschickt (beide Übersetzungspfade: legacy_exact-Lookup + _PHRASES).
4. DEFEKT, wenn die Ausgabe unverändert bleibt oder weiterhin deutsch aussieht.

Bekannte Grenze: Enum-/Statuswerte, die als Variable (nicht als Literal) an
die Anzeige gehen, sind statisch nicht erkennbar.

Exit-Code 0 = sauber, 1 = Defekte gefunden.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from i18n.translator import Translator  # noqa: E402
from i18n.qt_i18n import translate_source_text  # noqa: E402

FILES = [
    *sorted((ROOT / "ui").glob("*.py")),
    *sorted((ROOT / "logic").glob("*.py")),
    ROOT / "main.py",
]

VISIBLE_CALLS = {
    "QLabel", "QPushButton", "QGroupBox", "QRadioButton", "QCheckBox",
    "QAction", "QTableWidgetItem", "QListWidgetItem", "QMenu",
}
VISIBLE_METHODS = {
    "setWindowTitle", "setText", "setPlaceholderText", "addAction", "addItem",
    "addRow", "setHorizontalHeaderLabels", "setVerticalHeaderLabels",
    "setToolTip", "setStatusTip", "addMenu", "addTab", "setTitle",
    "information", "warning", "critical", "question", "getText", "getItem",
    "getInt", "getDouble",
}
VISIBLE_HELPERS = {
    "_card", "_summary_card", "row", "_note", "_styled_button", "_new_page",
    "_v_card", "_form_card", "_mk_btn",
}
# Strings, die explizit durch die Laufzeitbrücke geschickt werden, MÜSSEN
# dort auch ankommen — sonst ist der legacy_exact-/Phrase-Eintrag tot.
BRIDGE_CALLS = {"translate_source_text", "_translate_plain"}

_UMLAUT = re.compile(r"[äöüß]", re.IGNORECASE)
_GERMAN_TERMS = re.compile(
    r"\b(füller|tinte|tinten|feder|federn|papier|ausgaben|einstellung\w*|regel\w*|"
    r"hilfe|suche\w*|hinzufügen|löschen|bearbeiten|speichern|übernehmen|einfüllen|"
    r"gereinigt|reinigung|datenbank|pfad|durchsuchen|währung|sprache|darstellung|"
    r"allgemein|warnung|fehler|hinweis|bitte|kein|keine|tage|sperren|gesperrt|"
    r"überfällig|aktuelle\w*|letzte\w*|vorhanden\w*|neue\w*|größe\w*|kaufpreis|"
    r"kaufdatum|händler|beschreibung|kategorie|öffnen|schließen|abbrechen|"
    r"fortfahren|zurücksetzen|archiviert?\w*|sammlungswert|gesamt|verheiratet\w*|"
    r"einsätze|wert|leer\w*|gekauft|geplant|auswählen|anlegen|wechseln|prüfe\w*|"
    r"fällig|pflicht|vorschl\w*|belegung|nutzung|standzeit|wunsch\w*|bestellt|"
    r"mit|und|nicht|wurde|werden|zuerst|alle)\b",
    re.IGNORECASE,
)
_TARGET_EXEMPT = {
    "en": re.compile(r"\b(region|service|rest|mit|status|info)\b", re.IGNORECASE),
    "fr": re.compile(r"\b(papier|service|rest|page|date|info)\b", re.IGNORECASE),
}

_SYMBOL_ONLY = re.compile(r"^[\d\s.,'/:+\-–—|()%#×*=✓✕✅❌⚠ℹ⭐💍📦♻️🔧🖋✒🏠💰📋📊🧾⚙❔☰_{}<>]+$")
_SKIP_PREFIXES = ("QWidget", "QFrame", "QMainWindow", "#", "/*", "background:", "color:", "ui.", "nav.", "tour.")


def _func_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


# Empfaenger, deren warning/error/info nie auf dem Bildschirm landen. Die
# Methodennamen ueberschneiden sich mit QMessageBox.warning und wuerden sonst
# jede deutschsprachige Logzeile als unuebersetzten UI-Text melden. Logtexte
# sind fuer die Diagnose da und bleiben bewusst deutsch.
_LOGGER_EMPFAENGER = {"_log", "log", "logger", "logging", "_logger", "LOG", "LOGGER"}


def _ist_logaufruf(func: ast.AST) -> bool:
    if not isinstance(func, ast.Attribute):
        return False
    empfaenger = func.value
    if isinstance(empfaenger, ast.Name):
        return empfaenger.id in _LOGGER_EMPFAENGER
    if isinstance(empfaenger, ast.Attribute):
        return empfaenger.attr in _LOGGER_EMPFAENGER
    # logging.getLogger(__name__).warning(...) - der Aufruf selbst verraet es.
    if isinstance(empfaenger, ast.Call):
        return _func_name(empfaenger.func) == "getLogger"
    return False


def _strings_from(node: ast.AST) -> list[str]:
    out: list[str] = []
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        out.append(node.value)
    elif isinstance(node, ast.JoinedStr):
        out.append("".join(
            part.value if isinstance(part, ast.Constant) and isinstance(part.value, str) else "{}"
            for part in node.values
        ))
    elif isinstance(node, (ast.List, ast.Tuple)):
        for elt in node.elts:
            out.extend(_strings_from(elt))
    return out


def _looks_german(text: str) -> bool:
    return bool(_UMLAUT.search(text) or _GERMAN_TERMS.search(text))


def _is_candidate(text: str) -> bool:
    s = text.strip()
    if not s or len(s) > 600:
        return False
    if s.startswith(_SKIP_PREFIXES):
        return False
    if _SYMBOL_ONLY.fullmatch(s):
        return False
    if not any(c.isalpha() for c in s):
        return False
    return _looks_german(s)


def extract_candidates() -> dict[str, set[tuple[str, int, str]]]:
    """Sammelt {literal: {(datei, zeile, kontext)}} über alle Quelldateien."""
    candidates: dict[str, set[tuple[str, int, str]]] = {}
    for path in FILES:
        if path.name == Path(__file__).name:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        rel = str(path.relative_to(ROOT))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if _ist_logaufruf(node.func):
                continue
            name = _func_name(node.func)
            if name in BRIDGE_CALLS:
                kontext = "bridge"
            elif name in VISIBLE_CALLS or name in VISIBLE_METHODS or name in VISIBLE_HELPERS:
                kontext = "sink"
            else:
                continue
            for arg in node.args:
                if isinstance(arg, ast.Call) and _func_name(arg.func) == "t":
                    continue
                for text in _strings_from(arg):
                    if _is_candidate(text):
                        candidates.setdefault(text, set()).add((rel, getattr(node, "lineno", 0), kontext))
    return candidates


def main() -> int:
    tr = Translator.instance()
    candidates = extract_candidates()
    defects: list[str] = []
    for lang in ("en", "fr"):
        tr.set_language(lang)
        exempt = _TARGET_EXEMPT[lang]
        bad: list[str] = []
        for source in sorted(candidates):
            translated = translate_source_text(source, lang)
            unchanged = translated == source
            cleaned = exempt.sub("", translated)
            still_german = _UMLAUT.search(cleaned) or _GERMAN_TERMS.search(cleaned)
            if unchanged or still_german:
                locs = ", ".join(f"{p}:{ln}[{k}]" for p, ln, k in sorted(candidates[source])[:3])
                bad.append(f"{source!r} -> {translated!r} ({locs})")
        if bad:
            defects.append(f"{lang}: {len(bad)} sichtbare Strings nicht/unvollständig übersetzt")
            defects.extend("  - " + item for item in bad[:50])
            if len(bad) > 50:
                defects.append(f"  ... {len(bad) - 50} weitere")

    if defects:
        print("i18n visible text audit: FEHLER")
        for line in defects:
            print(line)
        return 1
    print(f"i18n visible text audit: OK ({len(candidates)} sichtbare Kandidaten via echtem translate_source_text für EN/FR geprüft)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
