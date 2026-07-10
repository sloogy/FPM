# FPM v0.2.55 – GitHub Release Ready Report

## Ergebnis

**Status:** GitHub Source Release Ready mit Auflagen für manuellen GUI-Smoke-Test.

Diese Version behebt die Release-Blocker aus der v0.2.54-Prüfung und ist für ein GitHub-Tag/Release vorbereitet.

## Umgesetzte Fixes

### Versionierung

- `APP_VERSION` auf `0.2.55` gesetzt.
- `APP_BUILD` auf `github-release-hardening` gesetzt.
- App-Beschreibung aktualisiert.

### Dokumentation / GitHub

- README auf v0.2.55 aktualisiert.
- `CHANGELOG_0.2.55_GITHUB_RELEASE_HARDENING.md` ergänzt.
- `RELEASE_NOTES_v0.2.55.md` ergänzt.
- `RELEASE_CHECKLIST_v0.2.55.md` ergänzt.
- GitHub Actions Workflow `.github/workflows/release-check.yml` ergänzt.

### Wishlist-Kaufworkflow

- Regression bleibt abgesichert:
  - Wunschfüller werden beim Kauf als aktive Füller erzeugt.
  - Füller-Widget reagiert auf externe `pens_changed`-Events.
  - Status `gekauft` im Bearbeiten-Dialog nutzt den echten Übernahme-Workflow.
  - explizite Sicherheitswerte bleiben gesetzt: `is_active=True`, `availability_status="available"`, `rotation_blocked=False`, `rotation_role="writer"`.

### i18n / Laufzeitübersetzung

Behoben:

- `Export abgeschlossen` erzeugt kein `Export abclosed` / `Export abfermé` mehr.
- `aktive InkLoad(s) geschlossen` ist jetzt explizit übersetzt.
- `Kein Limit` ist explizit übersetzt.
- Statuswerte wie `Aktiv`, `Leer`, `Archiv`, `Gefüllt` laufen über Keys.
- zentrale Wishlist-/Pen-/Ink-/Settings-/Rotation-Texte wurden weiter auf Keys gehärtet.
- Phrase-Fallback ersetzt einzelne Wörter nicht mehr innerhalb längerer Wörter.

### Tests

Neu ergänzt:

- Release-Metadaten-Test für v0.2.55.
- Regressionstest gegen i18n-Teilwortfehler.
- statische Prüfung bekannter Release-Blocker-Strings.

## Validierung

Ausgeführt:

```bash
python -m compileall -q .
pytest -q
python tools/i18n_audit.py
python tools/i18n_quality_audit.py
python tools/i18n_key_wiring_audit.py
python tools/i18n_runtime_audit.py
```

Ergebnis:

- `compileall`: OK
- `pytest`: 49/49 bestanden
- `i18n_audit`: OK, 1527 Keys × 3 Sprachen
- `i18n_quality_audit`: OK
- `i18n_key_wiring_audit`: OK
- `i18n_runtime_audit`: OK

## Nicht automatisch geprüft

- echter GUI-Start mit PySide6
- echte SQLite/SQLAlchemy-DB-Migration mit bestehenden Nutzerdaten
- visueller Sprachwechsel in der laufenden App
- Windows-/Linux-Build als ausführbare Anwendung
- GitHub Release wurde nicht direkt veröffentlicht, weil kein Ziel-Repository/Release-Zugriff im Auftrag festgelegt war

## GitHub Release Empfehlung

Empfohlener Ablauf:

```bash
git checkout -b release/v0.2.55
git add .
git commit -m "Release v0.2.55 GitHub hardening"
git push -u origin release/v0.2.55
```

Nach Merge:

```bash
git checkout main
git pull
git tag v0.2.55
git push origin v0.2.55
```

Release-Titel:

```text
FountainPen Manager v0.2.55 – GitHub Release Hardening
```

Release Notes:

- Inhalt aus `RELEASE_NOTES_v0.2.55.md` verwenden.

## Schlussurteil

**Für GitHub als Source Release bereit.**

Für einen öffentlichen Final-Release mit Endnutzer-Fokus sollte zusätzlich einmal lokal die GUI gestartet und der Wishlist-Kaufworkflow visuell geprüft werden.
