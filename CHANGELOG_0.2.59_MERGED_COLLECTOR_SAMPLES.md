# CHANGELOG v0.2.59 – Merge Collector Insights + Schreibproben

## Ziel

v0.2.59 vereinigt die beste Funktionalität aus zwei Varianten:

- `FPM v0.2.57 collector insights`: starke Sammler- und Statistikfunktionen.
- `FPM v0.2.58 RELEASE READY`: Schreibproben-Binder, Sammlungs-Advisor und BudgetManager-Export.

Der Release ist bewusst als Merge-Release umgesetzt: keine Experimente mit riskanten DB-Umbauten, sondern Integration der vorhandenen, testbaren Logik.

## Übernommen aus Collector Insights

- Sammlungswert-Übersicht in der Statistik:
  - Kaufwert
  - Marktwert
  - Versicherungswert
  - Wertänderung absolut und prozentual
- Wertentwicklung nach Jahr mit kumulierter Summe.
- Monats- und Jahresbudget in den Einstellungen.
- Budgetampel in der Statistik.
- Statistik-CSV-Export.
- Versicherungsliste-CSV-Export.
- Ranking „lange ungenutzt“ für Füller und Tinten.
- Regressionstests `tests/test_collector_insights.py`.

## Beibehalten aus v0.2.58

- Schreibproben-Modul mit Binder-Struktur.
- Verknüpfung von Schreibproben mit Füller, Tinte, Papier und Feder.
- Messwerte für Trockenzeit, Feathering, Durchschlag, Shading, Sheen, Fluss, Feedback und Gesamtbewertung.
- Automatische Gruppen „Highlights“ und „Prüfen“.
- Sammlungs-Advisor im Dashboard.
- BudgetManager-JSONL-Export.
- i18n sichtbarer Textaudit im Release-Workflow.

## Gelöste Merge-Probleme

- Versionen und Release-Metadaten auf `0.2.59` vereinheitlicht.
- README-Tag korrigiert.
- Collector-Insights-i18n-Keys mit Schreibproben-/Advisor-Keys zusammengeführt.
- Statistikmodul auf die Collector-Insights-Erweiterung gehoben, ohne das Schreibproben-Modul zu entfernen.
- Einstellungen enthalten jetzt sowohl Budgetgrenzen als auch BudgetManager-Export.
- `schema_version` auf `0.2.59` aktualisiert.

## Validierung

- `python -m compileall -q .` erfolgreich.
- `python -m pytest -q`: 66 Tests bestanden.
- Alle i18n-Audits erfolgreich.
