# v0.2.48 – Statistics Release Candidate

## Neu

- Neues Modul **Statistiken** in der Navigation.
- Ausgabenstatistik mit Filter nach Zeitraum:
  - Overall
  - Jahr
  - Monat
- Ausgabenstatistik mit Kategorie-Filter:
  - Füller
  - Tinte
  - Zubehör
  - Service
- Meistgenutzte Füller mit Zeitraum-Filter:
  - Woche
  - Monat
  - Jahr
  - Overall
- Meistgenutzte Tinten mit Zeitraum-Filter:
  - Woche
  - Monat
  - Jahr
  - Overall

## Logik

- Neue reine Statistik-Helfer in `logic/statistics_service.py`.
- Nutzungsranking basiert auf `InkLoad`-Historie:
  - Anzahl Befüllungen im Zeitraum
  - überlappende Nutzungstage im Zeitraum
  - erfasstes Volumen in ml
- Ausgaben werden aus `Expense` summiert und können in Standardwährung angezeigt werden.

## UI

- Neues Widget `ui/statistics_widget.py`.
- Statistik-Modul erscheint in der Navigation nach Ausgaben.
- Keine Datenbankmigration nötig.

## Tests

- Neue Tests für Zeitraumgrenzen, Ausgabenfilter und Nutzungsranking.
- `pytest`: 40 Tests bestanden.

## Hinweis

„Meistgenutzt“ bedeutet aktuell: Nutzung anhand der Füllhistorie (`InkLoad`).
Eine echte Schreibseiten-/Schreibsession-Zählung gibt es noch nicht.
