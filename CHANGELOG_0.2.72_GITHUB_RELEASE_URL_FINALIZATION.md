# Changelog – v0.2.72 GitHub Release URL Finalization

## Ziel

v0.2.72 schließt den letzten absichtlich offenen Release-Blocker aus v0.2.71: der Updater, die Manifest-Templates, der Installer und die Release-Dokumentation verwenden jetzt den echten GitHub-Release-Pfad.

## Geändert

- App-Version auf `0.2.72` erhöht.
- Build-Tag auf `github-release-url-finalization` gesetzt.
- GitHub-Release-Ziel gesetzt:
  - `https://github.com/sloogy/FPM/releases`
- Manifest-URL gesetzt:
  - `https://github.com/sloogy/FPM/releases/latest/download/latest.json`
- Download-URLs in `latest.json.template` und `docs/latest.json.template` auf `sloogy/FPM` umgestellt.
- `tools/sync_version.py` erzeugt ab jetzt Manifest-Templates mit echtem Repository-Pfad.
- `tools/build_windows.py` nutzt als Default-Base-URL den echten Release-Pfad.
- `ui/update_dialog.py` öffnet jetzt die echten GitHub-Releases.
- `updater/common.py` und `updater/github_manifest.py` laden `latest.json` vom echten Release-Ziel.
- `installer/FountainPenManager_Setup.iss` verwendet den echten Release-Link als Projekt-/Support-/Update-URL.
- I18N-Hinweise zum bisherigen Platzhalter aktualisiert.
- GUI-Smoke-Test-Dokumente DE/EN/FR auf v0.2.72 aktualisiert.
- Statische Release-Tests auf v0.2.72 nachgeführt.

## Nicht geändert

- Die SHA256-Werte in `latest.json.template` bleiben bewusst Platzhalter (`PUT_SHA256_HERE`). Diese müssen beim echten Release-Build nach Erzeugung der Artefakte gesetzt werden.
- Ein echter Qt-/Windows-GUI-Smoke-Test konnte in der Sandbox nicht ausgeführt werden, weil PySide6 hier fehlt.

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
i18n quality audit: OK

python tools/i18n_runtime_audit.py
i18n runtime audit: OK

python tools/i18n_key_wiring_audit.py
i18n key wiring audit: OK

python tools/i18n_visible_text_audit.py
i18n visible text audit: OK
```
