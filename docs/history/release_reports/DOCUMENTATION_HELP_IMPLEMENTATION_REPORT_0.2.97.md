# FPM v0.2.97 – Wiki- und Handbuch-Umsetzungsbericht

## Ziel

Die In-App-Hilfe und das Benutzerhandbuch wurden auf den tatsächlichen Funktionsstand der Version 0.2.97 gebracht. Im Mittelpunkt standen Auffindbarkeit, Mehrsprachigkeit, Laptop-Tauglichkeit und der Schutz vor Datenverlust bei der Füllererfassung.

## Umgesetzt

### In-App-Wiki

- Volltextsuche über Titel und Inhalte aller Hilfethemen.
- Mehrwortsuche: Alle eingegebenen Begriffe müssen im selben Hilfethema vorkommen.
- Sichtbare Rückmeldung bei Treffern und bei fehlenden Ergebnissen.
- Direkter Sprung zu einem Hilfethema aus dem aktuell geöffneten Programmreiter.
- Neuer Toolbar-Befehl **„Hilfe zum Reiter“**.
- Direkter Button zum Öffnen des Handbuchs in der gewählten Sprache.
- Neues Hilfethema zur sicheren Dateneingabe.
- Aktualisierte Beschreibung des Einfachmodus.
- Kürzere Reiternamen für Laptop-Fenster.
- Besserer Textkontrast innerhalb der Hilfe.
- Technische Legacy-Übersetzungsschlüssel durch sprechende Schlüssel ersetzt.

### Benutzerhandbücher

Vollständige Handbücher sind jetzt in drei Sprachen enthalten:

- `docs/BENUTZERHANDBUCH_DE.md`
- `docs/USER_MANUAL_EN.md`
- `docs/MANUEL_UTILISATEUR_FR.md`

Ergänzt oder aktualisiert wurden insbesondere:

- Dashboard-Kachelbedienung mit Einfach- und Doppelklick.
- Responsives Verhalten im Laptop- und Fenstermodus.
- Wiki-Suche und kontextbezogene Hilfe.
- Wechsel zwischen Füller-Formularseiten ohne Verlust bestätigter Werte.
- Eingabe von Werten mit `mm`, `g`, `ml` und lokalisierter Währung.
- Warnung vor dem Verwerfen ungespeicherter Füllerdaten.
- Neue FAQ-Einträge für kleine Displays, Formularwerte und Hilfezugriff.
- Versionsstand auf 0.2.97 aktualisiert.

### Datensicherheit im Füllerformular

Der Dialog erkennt Änderungen gegenüber dem Ausgangszustand. Beim Schließen oder Abbrechen mit ungespeicherten Änderungen erscheint eine klare Auswahl:

- weiter bearbeiten,
- Änderungen verwerfen.

Die Prüfung umfasst Stammdaten, Maße, Federdaten und Setup-Zuordnungen.

### Build und Release

- Alle drei Handbücher werden in den PyInstaller-Build aufgenommen.
- README, Changelog, Windows-Dokumentation und Versionsdateien wurden synchronisiert.
- Die GitHub-Release-Prüfung installiert nun die Laufzeitabhängigkeiten und erforderlichen Qt-Systembibliotheken, bevor Tests und GUI-Smoke-Test ausgeführt werden.
- Ein statischer Regressionstest verhindert, dass diese CI-Korrektur unbemerkt wieder entfernt wird.

## Validierung

| Prüfung | Ergebnis |
|---|---:|
| Pytest | 260 bestanden |
| GUI-Smoke-Test | bestanden |
| Versionssynchronisierung | bestanden |
| Python-Kompilierung | bestanden |
| i18n-Schlüssel | 2.089 × 3 Sprachen, bestanden |
| i18n-Qualität | 0 fehlende Übersetzungen, 0 Leaks |
| Sichtbare UI-Texte | bestanden |
| KILLCRITIC | 104.000 Prüfungen, 0 Findings |

## Ergebnis

Wiki und Anleitung entsprechen jetzt dem Funktionsstand der Version 0.2.97. Die Hilfe ist auffindbar, kontextbezogen, vollständig dreisprachig und im Release-Build enthalten. Die neue Schutzabfrage reduziert zusätzlich das Risiko, dass Nutzer eingegebene Füllerdaten versehentlich verwerfen.
