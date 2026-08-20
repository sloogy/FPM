# v0.2.31 – Settings Navigation UI

## Ziel
Die Einstellungsseite wurde von einer langen Endlosliste auf eine linke Kategorienavigation mit rechten Inhaltsseiten umgestellt. Jede Kategorie hat einen eigenen Scrollbereich.

## Umgesetzt
- Linke Settings-Navigation
- Rechte QStackedWidget-Seiten
- Eigene Seiten für Allgemein, Währung & Region, Datenbank & Backup, Import/Export, Reset/Gefahrenzone und Über
- Scrollbalken pro Kategorie statt einer überladenen Gesamtseite
- Factory Reset in eigener Gefahrenzone
- CSV-Export aus Datenbankbereich herausgelöst
- bestehende Funktionen beibehalten

## Ergebnis
Die Einstellungen sind deutlich ruhiger, besser skalierbar und für neue Optionen erweiterbar.
