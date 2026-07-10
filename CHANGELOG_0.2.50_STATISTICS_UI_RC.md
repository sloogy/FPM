# v0.2.50 – Statistics UI Release Candidate

## Statistik-UI
- Statistikseite in einen scrollbaren Bereich gelegt, damit kleinere Displays und hohe UI-Skalierung sauber funktionieren.
- Dynamische Zeitraum-Auswahl ergänzt:
  - Overall blendet Jahr/Monat/Woche aus.
  - Jahr zeigt nur die Jahresauswahl.
  - Monat zeigt Jahr + Monat.
  - Woche zeigt ein Datumsfeld mit regionalem Datumsformat.
- Jahr-Listen werden aus vorhandenen Ausgaben- und InkLoad-Daten befüllt.
- Füller- und Tintenranking haben nun getrennte Zeitraumfilter.
- Durchschnitt pro Ausgabe als eigene Kennzahlkarte ergänzt.

## Logik / Tests
- `summarize_expenses()` liefert zusätzlich `average_default`.
- Test für Durchschnitt pro Ausgabe ergänzt.
- Statistik-Service bleibt die zentrale, testbare Datenlogik.
