# Release Report – FountainPen Manager v0.2.72

## Kurzurteil

v0.2.72 ist die nachgezogene Release-Finalisierung zu v0.2.71. Der letzte absichtlich offene Blocker aus dem vorherigen Audit – der GitHub-/Updater-Releasepfad – ist jetzt auf das echte Repository gesetzt.

**Source-/Portable-RC:** Ja.  
**Updater-/Manifest-Freigabe:** Ja, technisch vorbereitet.  
**Öffentlicher Release:** Ja, sobald die echten Release-Artefakte mit SHA256-Werten hochgeladen sind.  
**Windows-Installer:** weiterhin erst nach manuellem GUI-Smoke-Test auf echter Windows-/PySide6-Umgebung endgültig freigeben.

## Umgesetzter Punkt 1

Gesetzter Release-Pfad:

```text
https://github.com/sloogy/FPM/releases
```

Gesetzte Manifest-URL:

```text
https://github.com/sloogy/FPM/releases/latest/download/latest.json
```

Betroffene Bereiche:

| Bereich | Status |
|---|---:|
| `updater/common.py` | Umgestellt |
| `updater/github_manifest.py` | Umgestellt |
| `ui/update_dialog.py` | Umgestellt |
| `latest.json.template` | Umgestellt |
| `docs/latest.json.template` | Umgestellt |
| `tools/sync_version.py` | Umgestellt |
| `tools/build_windows.py` | Umgestellt |
| `updater/generate_manifest.py` Beispiel | Umgestellt |
| `installer/FountainPenManager_Setup.iss` | Umgestellt |
| I18N-Hinweise DE/EN/FR | Umgestellt |
| GUI-Smoke-Test-Doku DE/EN/FR | Umgestellt |
| Tests | Auf v0.2.72 nachgeführt |

## Validierung

```text
python -m compileall -q .
OK

python -m pytest -q -ra
121 passed

python tools/sync_version.py --check
Alle Versionsdateien synchron: 0.2.72

python tools/i18n_audit.py
i18n audit: OK (1952 Keys × 3 Sprachen)

python tools/i18n_quality_audit.py
i18n quality audit: OK (0 untranslated, 0 leakage, 0 ternary literals)

python tools/i18n_runtime_audit.py
i18n runtime audit: OK

python tools/i18n_key_wiring_audit.py
i18n key wiring audit: OK

python tools/i18n_visible_text_audit.py
i18n visible text audit: OK
```

## GUI-Smoke-Test

```text
python tools/gui_smoke_test.py
SKIP: PySide6/runtime package missing: PySide6
Return code: 77
```

Das ist in dieser Umgebung kein Releasefehler, sondern eine fehlende Qt-/PySide6-Runtime. Vor dem finalen Windows-Release müssen diese Schritte auf echter Umgebung ausgeführt werden:

- `docs/GUI_SMOKE_TEST_DE.md`
- `docs/GUI_SMOKE_TEST_EN.md`
- `docs/GUI_SMOKE_TEST_FR.md`

## Noch zu beachten beim echten GitHub-Release

Die Manifest-Templates enthalten weiterhin bewusst:

```text
PUT_SHA256_HERE
```

Das ist korrekt für ein Template. Beim echten Release müssen nach dem Build die SHA256-Werte der erzeugten ZIP-/EXE-Artefakte eingetragen werden. Erst dann ist der automatische Updater praktisch nutzbar.

## Freigabeentscheidung

```text
Source-/Portable-RC: JA
Updater-URL/Manifest-Pfad: JA
Öffentlicher Release: JA, nach Upload echter Artefakte + SHA256
Windows-Installer: JA, nach manuellem GUI-Smoke-Test
```
