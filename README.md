# FountainPen Manager v0.2.89

FountainPen Manager ist eine offlinefähige Desktop-App für Füller, Tinten, Federn, Papier, Schreibproben, Rotation, Wartung, Ausgaben, Wishlist und Sammlerwert.

## Release-Fokus v0.2.89

v0.2.89 ist ein Packaging- und CI-Patch für v0.2.88. Die PyInstaller-Spezifikation wird nun versioniert und steht auch in frischen GitHub-Checkouts sowie Windows-Builds bereit.

v0.2.88 vereinheitlicht **alle Dezimal- und Währungsfelder**. Nicht mehr das Betriebssystem entscheidet, ob eine Eingabe mit Komma oder Punkt erscheint, sondern die in der App gewählte Region.

- Schweiz: `CHF 39.96`, Tausendertrennung `1'234.56`
- Deutschland/Österreich: `39,96 EUR`, Tausendertrennung `1.234,56`
- Frankreich: `39,96 EUR`, Tausendertrennung `1 234,56`
- Punkt und Komma werden bei der Eingabe sicher akzeptiert; `39,96` wird nie zu `3996`.
- Währungscodes bleiben sprachunabhängige ISO-Codes (`CHF`, `EUR`, `USD`, `GBP`).
- Kaufpreis, Marktwert, Versicherungswert, Servicekosten, Ausgaben, Wishlist, Papier, Tinten und Budgets verwenden dieselbe Logik.
- Währungswechsel im Dialog aktualisieren den sichtbaren Präfix/Suffix sofort.
- CSV-Import versteht lokale Zahlenformate und gängige Währungssymbole.
- Fehlende Währungsangaben werden als aktuelle Standardwährung behandelt, nicht fälschlich als CHF.

Zusätzlich enthält der Stand weiterhin die Härtungen aus v0.2.87:

- geführte Modulrunde mit Expertenfunktionen am Schluss;
- danach erste Tinte, ein bis zwei Füller und eine echte Rotation;
- reparierte Schnellaktion „Rotation vorschlagen“;
- keine automatisch eingespielten Beispiel-Tinten;
- vollständiges `.fpmbackup` mit Prüfsummen und Rollback;
- gehärtete Datenbankmigrationen, Updater und CI-Smoke-Tests;
- nicht-fatale Bildimporte: Ein Bildfehler verwirft keinen Füller und keine Schreibprobe;
- Recherche öffnet die ersten zwei tatsächlich relevanten Suchstufen.

## Technik

- Python 3.12+
- PySide6 / Qt
- SQLite und SQLAlchemy
- externe JSON-Sprachdateien für Deutsch, Englisch und Französisch
- portable Datenablage über `FPM_DATA_DIR`

## Start aus dem Quellcode

```bash
python -m pip install -r requirements.txt
python main.py
```

## Release-Prüfungen

```bash
python -m compileall -q .
python -m pytest -q
python tools/sync_version.py --check
python tools/i18n_audit.py
python tools/i18n_quality_audit.py
python tools/i18n_key_wiring_audit.py
python tools/i18n_runtime_audit.py
python tools/i18n_visible_text_audit.py
python tools/killcritic_1000_loop_audit.py
QT_QPA_PLATFORM=offscreen python tools/gui_smoke_test.py
```

## Dokumentation

- [Ausführliches Benutzerhandbuch](docs/BENUTZERHANDBUCH_DE.md)
- [Changelog v0.2.88](CHANGELOG_0.2.88_LOCALE_CURRENCY_HARDENING.md)
- [Releasebericht v0.2.88](RELEASE_REPORT_v0.2.88_LOCALE_CURRENCY_HARDENING.md)
- [Windows-Release-Anleitung](docs/WINDOWS_RELEASE_DE.md)

Der offizielle Releasepfad ist `https://github.com/sloogy/FPM/releases`.
