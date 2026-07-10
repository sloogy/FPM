# v0.2.57 – Collector Insights

Basis: v0.2.56. Schließt die letzten funktionalen Briefing-Lücken (außer
Diagrammen) und ergänzt eigenständige Features für Enthusiasten und Sammler.

## Neue Funktionen
- **Sammlungswert-Übersicht** in der Statistik: Kaufwert, aktueller Marktwert,
  Versicherungswert und Wertänderung (Δ absolut + %). Delta wird nur über
  Füller mit BEIDEN Werten gebildet, damit fehlende Marktwerte keine
  Scheinverluste erzeugen.
- **Wertentwicklung nach Jahr**: Käufe, Jahressumme und kumulierte Summe.
- **Budgetgrenzen** (Briefing): Monats-/Jahresbudget in den Einstellungen
  (0 = kein Limit, ohne Schema-Migration via AppSettings). Budgetampel in der
  Statistik: grün < 80 %, orange 80–100 %, rot > 100 %.
- **Statistik-CSV-Export** (Briefing): aktuelle Kennzahlen, Kategorien,
  Rankings und Sammlungswert als CSV (Semikolon, UTF-8-BOM für Excel).
- **Versicherungsliste-Export**: aktive Sammlung mit Kaufdatum, Kaufpreis,
  Marktwert und Versicherungswert als CSV — für Versicherung/Inventar.
- **„Lange ungenutzt"-Ranking** für Füller und Tinten (Enthusiasten-Feature):
  Tage seit letzter Nutzung aus der InkLoad-Historie, nie benutzte zuoberst.

## Technik
- 6 neue Pure-Logic-Funktionen in `logic/statistics_service.py`, vollständig
  ohne DB/GUI testbar (Duck-Typing, optionale Währungsumrechnung via Callable).
- 9 neue Tests (`tests/test_collector_insights.py`), Suite: 58 Tests.
- 28 neue i18n-Keys in DE/EN/FR (1566 Keys × 3).

## Validierung
- python -m compileall -q . ✅ · 58/58 Tests ✅ · alle 5 i18n-Audits ✅

## Nicht automatisch geprüft
- GUI-Laufzeit (Layout der neuen Statistik-Sektion, Exportdialoge, Budget-Ampelfarben)
- Diagramme bleiben bewusst offen: ohne GUI-Runtime nicht verifizierbar,
  Empfehlung als eigener Schritt nach dem Smoke-Test.
