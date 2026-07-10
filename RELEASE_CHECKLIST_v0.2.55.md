# GitHub Release Checklist – v0.2.55

## Vor dem Commit

- [ ] Arbeitsordner enthält keine `__pycache__`-Ordner
- [ ] `.pytest_cache` entfernt
- [ ] `app_info.py` zeigt `APP_VERSION = "0.2.55"`
- [ ] README zeigt v0.2.55
- [ ] Changelog für v0.2.55 vorhanden
- [ ] Release Notes für v0.2.55 vorhanden

## Lokal prüfen

```bash
python -m compileall -q .
python -m pytest -q
python tools/i18n_audit.py
python tools/i18n_quality_audit.py
python tools/i18n_key_wiring_audit.py
python tools/i18n_runtime_audit.py
```

Erwartung:

- 49 Tests bestanden
- alle i18n-Audits grün

## GitHub Commit

```bash
git checkout -b release/v0.2.55
git add .
git commit -m "Release v0.2.55 GitHub hardening"
git push -u origin release/v0.2.55
```

Dann Pull Request erstellen oder direkt nach `main` mergen.

## Tag setzen

Nach Merge auf `main`:

```bash
git checkout main
git pull
git tag v0.2.55
git push origin v0.2.55
```

## Release in GitHub erstellen

- Tag: `v0.2.55`
- Titel: `FountainPen Manager v0.2.55 – GitHub Release Hardening`
- Release Notes: Inhalt aus `RELEASE_NOTES_v0.2.55.md`
- Source ZIP als Asset optional zusätzlich hochladen

## Nach Release prüfen

- [ ] GitHub Actions Release Check ist grün
- [ ] Release-Tag zeigt auf den richtigen Commit
- [ ] Download-ZIP enthält `app_info.py` mit v0.2.55
- [ ] README/Release Notes stimmen
