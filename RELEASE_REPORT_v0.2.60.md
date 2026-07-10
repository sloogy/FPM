# Release Report – FPM v0.2.60

## Status

Release Candidate mit optionalem Enthusiasten-Lab.

## Umgesetzt

1. Tinten-Restmengen / Nachkaufen
   - Restmenge, Füllstand, Nachkauf-Schwelle, Nachkauf-Link und Notiz.
   - Logik bleibt optional und tolerant gegenüber fehlenden Daten.

2. Schreibproben-Vergleichsansicht
   - Zwei bis vier Schreibproben nebeneinander.
   - Automatischer Score, Fazit und Gewinner-Empfehlung.

3. Feder-Tausch-Historie
   - Anzeige aktiver und historischer Pen-Nib-Setups pro Füller.
   - Optionale Gründe/Notizen für Einbau und Ausbau vorbereitet.

4. Farbfamilien-Lückenanalyse
   - Erkennt grobe Farbfamilien und Unterlücken wie warmes Braun.

5. Reinigungsprotokoll
   - Neue Tabelle `cleaning_logs`.
   - Dauer, Aufwand, Spülgänge, Reiniger, Ergebnis und Notizen.
   - Statistik pro Tinte.

## Validierung

- Compile-Check
- Regressionstests
- i18n-Audits DE/EN/FR

## Manuell lokal prüfen

- App starten.
- Enthusiasten-Lab öffnen.
- Tinten-Restmenge bearbeiten.
- Zwei Schreibproben markieren und vergleichen.
- Reinigung protokollieren.
