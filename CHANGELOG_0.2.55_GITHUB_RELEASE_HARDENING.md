# v0.2.55 – GitHub Release Hardening

## Status

**Release-Empfehlung:** GitHub-Release-Candidate / Source Release.

Diese Version behebt die Release-Blocker aus der Prüfung von v0.2.54 und ist für einen GitHub-Release vorbereitet. Ein echter GUI-Smoke-Test mit installierter PySide6/SQLAlchemy-Runtime bleibt vor einer breiten Veröffentlichung empfohlen.

## Behoben

- Interne Versionierung auf `0.2.55` aktualisiert.
- Build-Kennung auf `github-release-hardening` gesetzt.
- README auf aktuellen Release-Stand gebracht.
- Release Notes und GitHub-Release-Checkliste ergänzt.
- GitHub Actions Workflow `release-check.yml` ergänzt.
- Wishlist-Kaufübernahme bleibt regressionsgesichert:
  - gekaufte Wunschfüller werden aktive Sammlungseinträge,
  - Füller-Tab reagiert auf `pens_changed`,
  - Bearbeiten-Dialog nutzt den echten Transferworkflow.
- i18n-Mischtexte behoben:
  - `Export abgeschlossen` wird nicht mehr zu `Export abclosed` / `Export abfermé`,
  - `aktive InkLoad(s) geschlossen` ist jetzt explizit übersetzt,
  - `Kein Limit`, Statuswerte und zentrale Dialogtexte laufen über i18n-Keys.
- Zusätzliche Regressionstests für Release-Version, i18n-Teilwortfehler und bekannte UI-Blocker ergänzt.

## Validierung

- `python -m compileall -q .` ✅
- `python -m pytest -q` ✅, 49 Tests bestanden
- `python tools/i18n_audit.py` ✅
- `python tools/i18n_quality_audit.py` ✅
- `python tools/i18n_key_wiring_audit.py` ✅
- `python tools/i18n_runtime_audit.py` ✅

## Bekannte Einschränkungen

Nicht automatisch geprüft:

- echter GUI-Start mit PySide6
- echte Datenbankmigration mit bestehenden Nutzer-Datenbanken
- visueller Sprachwechsel in der laufenden App
- Windows-/Linux-Paketbau als ausführbare Anwendung

## Empfehlung

Für GitHub als Source-Release taggen. Vor einem breiteren Final-Release zusätzlich einmal lokal starten und die wichtigsten Seiten manuell prüfen.
