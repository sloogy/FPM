# FountainPen Manager v0.2.7 – Ausgaben & Sidebar

## Fokus
Diese Version vervollständigt den Ausgaben-Tracker und verbessert die Sichtbarkeit der linken Navigation.

## Neu im Ausgaben-Tracker
- Ausgaben können jetzt bearbeitet werden.
- Währung wählbar: CHF, EUR, USD, GBP.
- Händler / Anbieter erfassbar.
- Bestellnummer / Rechnungsnummer erfassbar.
- Zahlungsart erfassbar.
- Garantie- oder Servicefrist erfassbar.
- Ausgabe kann mit Füller, Tinte, Feder oder Papier verknüpft werden.
- Serviceausgaben können mit Füllern verbunden bleiben.
- Kategorie-Filter ergänzt.
- Detailpanel rechts ergänzt.
- Summen werden getrennt nach Währung angezeigt.

## Datenbank
Neue Felder in `expenses`:
- `nib_id`
- `vendor`
- `order_number`
- `payment_method`
- `warranty_until`

## Sidebar
- Breiter: 240 px.
- Dunklerer Hintergrund.
- Größere Schrift.
- Höhere Navigationsbuttons.
- Aktives Modul stärker hervorgehoben.

## Hinweis
Bestehende Datenbanken werden per einfacher SQLite-Migration erweitert. Bestehende Ausgaben bleiben erhalten.
