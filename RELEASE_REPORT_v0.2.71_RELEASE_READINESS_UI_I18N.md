# Release Report – FountainPen Manager v0.2.71

> Historischer Report: Dieser Stand wurde durch v0.2.72 abgelöst. Der damals offene GitHub-/Updater-Punkt ist in v0.2.72 mit https://github.com/sloogy/FPM/releases umgesetzt.

## Kurzurteil

v0.2.71 ist ein gehärteter Source-/Portable-Release-Kandidat auf Basis von v0.2.70.

**Öffentlicher Final Release:** eingeschränkt, solange der Updater-/GitHub-OWNER-Punkt bewusst offen bleibt.  
**Interner RC / Source-Paket:** ja.  
**Windows-Installer:** erst nach echtem Windows-GUI-Smoke-Test freigeben.

## Umgesetzte Auditpunkte

| Auditpunkt | Status |
|---|---:|
| 1. Updater-/OWNER-Platzhalter ersetzen/deaktivieren | Nicht umgesetzt, explizit ausgenommen |
| 2. README auf aktuelle Version bringen | Umgesetzt |
| 3. Windows-Doku auf aktuelle Version bringen | Umgesetzt |
| 4. Runtime-I18N-Leaks aus Rotation/Regeln/Auto-Modus entfernen | Umgesetzt |
| 5. GUI-Smoke-Test absichern | Dokumentiert + automatischer Kurztest ergänzt |
| 6. Sidebar gruppieren / DAU-Navigation verbessern | Umgesetzt |

## Validierung

```text
python -m compileall -q .
OK

python -m pytest -q -ra
121 passed

python tools/sync_version.py --check
Alle Versionsdateien synchron: 0.2.71

python tools/i18n_audit.py
OK – 1952 Keys × 3 Sprachen

python tools/i18n_quality_audit.py
OK

python tools/i18n_key_wiring_audit.py
OK

python tools/i18n_runtime_audit.py
OK

python tools/i18n_visible_text_audit.py
OK
```

## GUI-Smoke-Test in dieser Umgebung

```text
python tools/gui_smoke_test.py
SKIP: PySide6/runtime package missing: PySide6
Return code: 77
```

Das ist kein Codefehler, sondern eine Umgebungsgrenze der Sandbox. Der manuelle GUI-Smoke-Test bleibt vor Final Release Pflicht:

- `docs/GUI_SMOKE_TEST_DE.md`
- `docs/GUI_SMOKE_TEST_EN.md`
- `docs/GUI_SMOKE_TEST_FR.md`

## Bekannter offener Punkt

Die folgenden Platzhalter sind weiterhin vorhanden, weil Punkt 1 explizit ausgenommen wurde:

```text
sloogy/FPM
```

Betroffene Bereiche bleiben damit für einen echten öffentlichen Update-/Installer-Release kritisch:

- Update-Dialog
- Manifest-URL
- GitHub-Release-Links
- Installer-Projekt-URL

## Freigabeentscheidung

```text
Source-/Portable-RC: JA
Öffentlicher Final Release: Historisch eingeschränkt; in v0.2.72 nachgezogen
Windows-Installer-Release: NUR NACH MANUELLEM GUI-SMOKE-TEST
Updater-Freigabe: Historisch nein; in v0.2.72 auf https://github.com/sloogy/FPM/releases gesetzt
```
