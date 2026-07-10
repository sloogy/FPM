# Release-Audit – FountainPen Manager v0.2.73

**Basis:** v0.2.72 (github-release-url-finalization)
**Build:** i18n-leak-fixes-release-audit
**Datum:** 6. Juli 2026

## Kurzurteil

**Source-/Portable-RC: JA.** v0.2.72 war bereits ein reifer, ehrlich
dokumentierter Stand. Die kritische Prüfung hat die Behauptungen des letzten
Reports **unabhängig bestätigt** (121 Tests, 1952 Keys × 3, alle Audits grün,
GitHub-URLs konsistent auf `sloogy/FPM`) und zwei reale Defekte gefunden, die
die Audits methodisch nicht fangen konnten. Beide sind behoben.

## Kritisch geprüft (nicht Reports geglaubt)

- **Key-Parität hart nachgerechnet:** de = en = fr = 1955, 0 Waisen.
- **Alle 1488 statischen `t()`-Keys** existieren in allen drei Sprachen →
  keine Roh-Key-Anzeige.
- **GitHub-/Updater-Pfade** verifiziert: durchgängig `sloogy/FPM`, keine
  Fremd-Platzhalter (nur das bewusste `PUT_SHA256_HERE` im Template bleibt).
- **Logik-Module** auf hartcodierte deutsche Rückgaben geprüft → nur englische
  Enum-Codes (`"service"`, `"fine"` …), keine sichtbaren Texte.
- **Regressions-Check** der Klarheits-Features: Dashboard blendet leere
  Abschnitte weiter aus, Kontextmenüs und die neue gruppierte Seitenleiste
  (`GROUPED_ORDER`) sind vorhanden. Alle sechs Listen nutzen einheitlich
  `EmptyStateWidget`.

## Behobene Fehler

### 1. Hartcodierte deutsche UI-Strings im Füllerbereich (EN/FR-Leak)
Fünf sichtbare Strings in `ui/pen_widget.py` waren nicht über `t()` geführt und
rutschten am Wiring-Audit vorbei, weil sie an Variablen zugewiesen bzw. in
f-Strings eingebettet waren:

| Stelle | Vorher | Nachher |
|---|---|---|
| Status-Chips der Füllerliste | `'🔧 Service' / '🧼 Austrocknung' / '🔒 Gesperrt'` | `_status_label(...)` (übersetzt) + Emoji-Map |
| Warntext Sperrfrist | `f'Rotation gesperrt{...}'` | `t('ui.pen_widget.rotation_blocked')` |
| Datumszusatz (2×) | `f' bis {datum}'` | `t('ui.pen_widget.until_suffix', date=...)` |
| Service-Hilfe-Fußzeile | hartcodierter deutscher HTML-Absatz | `t('ui.pen_widget.service_help_footer')` |

Die Fußzeile war zusätzlich sprachwidrig: Der Hilfetext-Body ist sprachabhängig,
die Fußzeile blieb aber immer deutsch. Für EN/FR-Nutzer erschien deutsche
Sprache mitten in der Oberfläche. Jetzt sauber übersetzt (DE/EN/FR).

Die Status-Chips nutzen jetzt denselben Übersetzungsmechanismus wie das
Dashboard (`dashboard.status_labels.*`) – dadurch auch **inhaltlich konsistent**
(z. B. „In Service" / „Austrocknungsrisiko" statt abweichender Kurzformen).

### 2. Falsche Fremdversion im Release-Tooling
`updater/generate_manifest.py` referenzierte an mehreren Stellen die Version
**2.2.9** (Docstring-Beispiel und argparse-Hilfetexte). Das ist die Version des
BudgetManager-Projekts und gehört nicht in FPM – wer den Beispielbefehl kopiert,
hätte ein Manifest mit falscher Version erzeugt. Auf `0.2.73` korrigiert; ein
neuer Guard-Test hält Fremdversionen dauerhaft fern.

## Neue Guard-Tests
`tests/test_i18n_pen_leak_fixes_static.py` (GUI-frei): stellt sicher, dass die
hartcodierten deutschen Strings nicht zurückkehren, die neuen Keys in allen
Sprachen existieren (inkl. `{date}`-Platzhalter) und keine Fremdversion im
Manifest-Tool auftaucht. Der Test hat beim Bump direkt zusätzliche
2.2.9-Vorkommen in den argparse-Hilfetexten aufgedeckt.

## Validierung

```text
python -m compileall -q .            → OK (gesamter Baum)
Testsuite (headless Logik-Harness)   → 124 passed (+3 ggü. v0.2.72)
tools/sync_version.py --check        → Alle Versionsdateien synchron: 0.2.73
tools/i18n_audit.py                  → OK (1955 Keys × 3 Sprachen)
tools/i18n_quality_audit.py          → OK (0 untranslated, 0 leakage)
tools/i18n_runtime_audit.py          → OK
tools/i18n_key_wiring_audit.py       → OK
tools/i18n_visible_text_audit.py     → OK
Key-Parität (eigenes Skript)         → de=en=fr=1955, 0 Waisen
Static t()-Keys existieren           → 1488/1488
Fremdversion 2.2.x im Projekt        → keine (außer Guard-Assertion)
```

## Ehrliche Einschränkungen

- **Kein GUI-Smoke-Test:** PySide6 fehlt in der Sandbox
  (`tools/gui_smoke_test.py` → Return 77 = SKIP). Die geänderten Stellen sind
  reine String-/Übersetzungsersetzungen entlang bestehender Muster und
  kompilieren, wurden aber nicht in einem Desktop-Fenster geöffnet. Vor dem
  finalen Windows-Release: Füllerliste mit einem Füller im Service-/Sperrstatus
  ansehen (Status-Chip + Sperrfrist), und die Service-Hilfe auf EN/FR prüfen.
- **SHA256 im Manifest-Template** bleibt bewusst `PUT_SHA256_HERE` – erst beim
  echten Build mit den Artefakt-Hashes zu füllen.
- **`test_logic_migration_hardening.py`** braucht SQLAlchemy und läuft in der
  echten Dev-/CI-Umgebung, nicht in dieser Sandbox.

## Freigabeentscheidung

```text
Source-/Portable-RC:        JA
Updater-URL/Manifest-Pfad:  JA (sloogy/FPM, konsistent)
i18n-Konsistenz DE/EN/FR:   JA (Füller-Leaks behoben)
Öffentlicher Release:       JA, nach Upload echter Artefakte + SHA256
Windows-Installer:          JA, nach manuellem GUI-Smoke-Test
```
