# FountainPen Manager v0.2.55

## Kurzfassung

v0.2.55 ist ein GitHub-Release-Hardening nach der v0.2.54-Prüfung. Die Version korrigiert die Release-Versionierung, stabilisiert die Wishlist-Kaufübernahme, behebt kritische i18n-Mischtexte und ergänzt Regressionstests sowie einen GitHub-Actions-Releasecheck.

## Highlights

- Version intern korrekt auf `0.2.55` gesetzt.
- GitHub-Release-Workflow ergänzt.
- Wishlist → gekauft → Sammlung bleibt abgesichert.
- i18n-Teilwortfehler behoben.
- 49 Tests bestanden.
- i18n-Audits grün.

## Manuelle Prüfung vor Veröffentlichung

Empfohlen vor dem Klick auf „Publish release“:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pytest
python -m compileall -q .
python -m pytest -q
python tools/i18n_audit.py
python tools/i18n_quality_audit.py
python tools/i18n_key_wiring_audit.py
python tools/i18n_runtime_audit.py
python main.py
```

Danach in der App prüfen:

- Startet die App?
- Wird Version `0.2.55` angezeigt?
- Wishlist-Wunschfüller als gekauft übernehmen → erscheint in Füllerverwaltung?
- Sprache EN/FR: keine Mischtexte wie `abclosed`, `abfermé`, `Aucun Limit`?
- Statistikseite öffnet?
- Dashboard zeigt Safety Timer ohne Fehler?

## GitHub Release

Empfohlener Tag:

```bash
git tag v0.2.55
git push origin v0.2.55
```

Release-Titel:

```text
FountainPen Manager v0.2.55 – GitHub Release Hardening
```
