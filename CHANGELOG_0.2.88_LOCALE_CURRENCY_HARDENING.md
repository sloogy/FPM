# Changelog v0.2.88 – Locale & Currency Hardening

## Einheitliche Zahlen- und Währungslogik

- Neue zentrale `LocalizedDoubleSpinBox`: Alle Dezimalfelder folgen der App-Region statt der Betriebssystem-Locale.
- Komma und Punkt werden bei der Eingabe akzeptiert; Faktor-100/1000-Fehlinterpretationen wie `39,96 → 3996` sind verhindert.
- Gemischte Schreibweisen werden verstanden: `1.234,56`, `1,234.56`, `1'234.56` und `1 234,56`.
- Währungsposition und Dezimaltrennzeichen werden einheitlich aus `LocaleService` bezogen.
- Währungspräfix/-suffix aktualisiert sich sofort beim Wechsel der Währung und bei einer live geänderten Region.
- Dezimal- und Tausender-Auswahl sind als getrennte Radiobutton-Gruppen verdrahtet; sie können sich nicht mehr gegenseitig abwählen.
- Frankreichs Leerzeichen-Gruppierung (`1 234,56`) ist jetzt in der Oberfläche auswählbar und wird korrekt gespeichert.
- Identische Dezimal- und Tausendertrennzeichen werden blockiert; beschädigte Alt-Einstellungen werden fail-safe bereinigt.
- „Kein Tausendertrennzeichen“ bleibt nach einem Neustart erhalten und fällt nicht mehr unbemerkt auf Apostroph zurück.
- Kaufpreis, Marktwert, Versicherungswert, Servicekosten, Ausgaben, Wishlist, Tinten, Papier und Budgetgrenzen verwenden dieselbe Komponente.

## Stabile Währungscodes

- ISO-Codes werden nicht mehr übersetzt.
- `CHF`, `EUR`, `USD` und `GBP` sind in Deutsch, Englisch und Französisch identisch.
- Fehler behoben, durch den englische Oberflächen `CHF` als `USD` und französische Oberflächen `CHF` als `EUR` anzeigen konnten.
- CSV-Import normalisiert ISO-Codes sowie `Fr.`, `SFr`, `€`, `$`, `US$` und `£`.
- Unbekannte oder fehlende Codes fallen kontrolliert auf die eingestellte Standardwährung zurück.

## Umrechnung und Wechselkurse

- Fehlende Währungsangaben werden bei der Umrechnung als Standardwährung interpretiert, nicht mehr implizit als CHF.
- Wechselkurse werden locale-sicher eingelesen.
- Nichtnumerische, nicht endliche oder nichtpositive Wechselkurse werden abgelehnt statt still ersetzt.
- Ungültige gespeicherte Kurse werden beim Laden verworfen; CHF bleibt als Basis bei `1.0`.
- Die Vorschau in den Einstellungen zeigt nur noch das tatsächlich aktive Format.

## Anzeige und Import

- Wishlist, Ausgabenhistorie und Tinten-Reichweitenkosten verwenden `format_money()` statt eigener Stringformate.
- CSV-Import für Füller und Tinten verwendet denselben robusten Zahlenparser wie die Oberfläche.
- Maschinenlesbare Speicherung bleibt unverändert numerisch; die Darstellung ist davon sauber getrennt.

## Übernommene Release-Härtungen

- Modulrunde mit Expertenfunktionen am Schluss; anschließend Tinte, ein bis zwei Füller und Rotation.
- Schnellaktion erzeugt echte Rotationsvorschläge.
- Keine automatisch angelegten Beispiel-Tinten.
- Vollbackup/Restore, Migrations-, Updater- und CI-Härtung bleiben erhalten.
- Bildimporte sind nicht-fatal; fehlgeschlagene Bilder verwerfen keine Datensätze.
- Recherche öffnet die ersten zwei relevanten Suchstufen.

## Tests

- Neue Regressionstests für Parsing, Formatierung, ISO-Codes, dynamische Affixe, Umrechnung und die Verwendung der zentralen Qt-Komponente.
- Bestehende Tour-, Rotation-, Backup-, Updater-, Media- und i18n-Tests bleiben aktiv.
