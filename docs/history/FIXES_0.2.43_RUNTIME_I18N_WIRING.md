# v0.2.43 – Runtime i18n Wiring

Diese Version korrigiert den irreführenden Stand von v0.2.41/v0.2.42: Die Übersetzungsdateien waren vollständig, aber große Teile der sichtbaren UI waren weiterhin hart auf Deutsch verdrahtet.

## Änderungen

- Neues Modul `i18n/qt_i18n.py`:
  - übersetzt sichtbare Qt-Texte zur Laufzeit aus deutschen Source-Strings
  - nutzt zuerst die vorhandenen JSON-Übersetzungen
  - ergänzt Legacy-UI-Texte über kuratierte Source-String- und Phrase-Maps
  - übersetzt Widgets, Dialoge, Menüs, Toolbars, Tabellenköpfe, Listen, Tabs, Placeholders und statische MessageBox/FileDialog/InputDialog-Texte
- `main.py` installiert die i18n-Hooks direkt nach dem Laden der gespeicherten Sprache.
- `MainWindow` wendet Übersetzungen nach Lazy-Widget-Erstellung und nach Refreshs erneut an.
- Spracheinstellung wird nun sofort angewendet statt erst nach Neustart.
- Neues CI-taugliches Audit `tools/i18n_runtime_audit.py`:
  - extrahiert wahrscheinlich sichtbare Qt-Strings aus `ui/*.py` und `main.py`
  - prüft, ob diese für EN/FR nicht deutsch bleiben

## Ehrliche Einschränkung

Dies ist funktional ein echter UI-Wiring-Fix. Die deutsche Source-Sprache bleibt aber in vielen älteren Widget-Dateien weiterhin als Fallback-Literal enthalten. Das ist absichtlich so, damit der Patch risikoarm bleibt und keine hunderten UI-Aufrufe manuell umgebaut werden müssen. Langfristig können diese Literale schrittweise in echte `t("...")`-Keys überführt werden.

## Tests

```bash
python tools/i18n_audit.py
python tools/i18n_runtime_audit.py
python -m compileall -q .
```

Erwartetes Ergebnis:

```text
i18n audit: OK (232 Keys × 3 Sprachen)
i18n runtime audit: OK (... likely visible German UI strings covered for EN/FR)
compileall: OK
```
