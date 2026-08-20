# Release Report v0.2.59 – Merge & Releasefähigkeit

## Ergebnis

v0.2.59 ist der zusammengeführte Release aus Collector Insights und Schreibproben-Enthusiasten-Labor. Die Version enthält die besten Funktionen beider Varianten und behebt die wichtigsten Merge- und Release-Inkonsistenzen.

## Releasefähigkeit

**Status: Release Candidate / Source-Release bereit.**

Die statisch prüfbaren Punkte sind sauber:

- Syntax/Compile-Check erfolgreich.
- 66 Regressionstests erfolgreich.
- i18n-Audits für DE/EN/FR erfolgreich.
- Release-Metadaten, README und Schema-Version sind konsistent auf `0.2.59`.
- Keine direkte BudgetManager-Datenbankkopplung; Export bleibt kontrolliert als JSONL.

## Vergleich der Varianten

### v0.2.57 collector insights – Stärken

- Sammlungswert und Wertentwicklung.
- Budgetampel für Hobby-Ausgaben.
- CSV-Export für Statistik und Versicherung.
- „Lange ungenutzt“-Ranking für Rotation und Wiederentdeckung.

### v0.2.58 release ready – Stärken

- Schreibproben-Binder wie ein kleines Erfahrungsarchiv.
- Dashboard-Sammlungs-Advisor.
- BudgetManager-Export.
- Erweiterter Release-Workflow mit sichtbarem i18n-Audit.

### Merge-Entscheidung

v0.2.58 wurde als Basis behalten, weil dort die neuere Navigationsstruktur, Schreibproben-Datenbanktabelle und Exportlogik enthalten waren. Die Collector-Insights-Funktionen wurden gezielt in Statistik, Einstellungen, i18n und Tests integriert.

## Enthusiasten-Nutzen

- Sammlung wird nicht nur verwaltet, sondern bewertet und analysiert.
- Gute Kombinationen werden als Schreibproben dokumentierbar.
- Problemkombinationen bleiben auffindbar.
- Versicherungs- und Marktwertsicht hilft bei Sammlungen mit höherem Wert.
- Lange nicht genutzte Füller/Tinten werden sichtbar.
- Budgetgrenzen verhindern, dass Hobby-Ausgaben unbemerkt auslaufen.

## Nicht automatisch geprüft

Der echte PySide6-GUI-Start konnte in der Sandbox nicht zuverlässig als Endnutzer-Smoke-Test geprüft werden. Die Source-, Logik-, i18n- und DB-nahen Prüfungen sind erfolgreich. Für den finalen Tag empfiehlt sich zusätzlich ein manueller GUI-Smoke-Test:

1. App starten.
2. Statistik öffnen.
3. Schreibproben öffnen.
4. Einstellungen öffnen und Budgetgrenzen speichern.
5. BudgetManager-Export testweise in eine Datei schreiben.
6. Statistik- und Versicherungsexport testen.
