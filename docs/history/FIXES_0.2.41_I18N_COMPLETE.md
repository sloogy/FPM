# v0.2.41 – i18n Complete

Bereinigung und Vervollständigung der Übersetzungsdateien.

## Fixes

- `de.json`, `en.json` und `fr.json` haben jetzt dieselbe Key-Struktur.
- Fehlende englische und französische Übersetzungen wurden ergänzt.
- Veraltete `app.version`-Einträge in den Sprachdateien wurden auf `v0.2.41` aktualisiert.
- `Translator` nutzt nun Deutsch als Fallback, falls ein Key in einer aktiven Sprache fehlt.
- `Translator` kann die gespeicherte Sprache beim App-Start aus `AppSettings` laden.
- `main.py` lädt die Sprache nach `init_db()`.
- Französisch ist in den allgemeinen Einstellungen auswählbar.
- Neues Audit-Tool `tools/i18n_audit.py` prüft Key-Parität und leere Übersetzungen.

## Prüfung

```bash
python3 tools/i18n_audit.py
python3 -m compileall -q .
```

Erwartet:

```text
i18n audit: OK (144 Keys × 3 Sprachen)
```
