# v0.2.49 – Statistics Locale Release Candidate

## Polishes

- Datumsformat als eigene Einstellung in **Währung & Region** ergänzt.
- Regionsvoreinstellungen setzen jetzt auch das passende Datumsformat:
  - CH/DE/AT/EU: `DD.MM.YYYY`
  - FR/GB: `DD/MM/YYYY`
  - US: `MM/DD/YYYY`
  - manuell zusätzlich: `YYYY-MM-DD`
- `LocaleService` formatiert Datumswerte nun zentral über `format_date()`.
- `QDateEdit`-Felder in Statistik, Ausgaben, Füller-, Tinten- und Papierdialogen übernehmen das gewählte Datumsformat.
- Statistik-Tabellen und Zeitraumhinweise nutzen das zentrale Datumsformat.
- Top-Karten in der Statistik sind lokalisiert: `Tage/days/jours` statt hartem `d`.
- Ausgabenfilter in den Statistiken enthält wieder alle Release-Kategorien:
  Füller, Tinte, Feder, Papier, Zubehör, Service, Versand, Zoll, Sonstiges.

## Tests / Checks

- Neue Tests für Datumsformatierung und vollständige Ausgabenkategorien.
- `pytest`: 42 Tests bestanden.
- `compileall`: OK.
- i18n-Audits: OK.
