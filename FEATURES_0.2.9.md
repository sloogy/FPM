# v0.2.9 – Ausgaben-Sync & Rotation übernehmen

## Neu
- Rotationsvorschläge können jetzt direkt mit einem sichtbaren Button `✓ Übernehmen` bestätigt werden.
- Doppelklick auf einen Vorschlag übernimmt ihn ebenfalls.
- Rechtsklick-Menü bleibt als Zusatz erhalten.
- Füller-Kaufpreis wird automatisch als Ausgabe im Ausgaben-Tracker gespiegelt.
- Wenn der Kaufpreis im Füller geändert wird, wird der automatische Ausgaben-Eintrag aktualisiert.
- Wenn eine verknüpfte Ausgabe bearbeitet/gelöscht wird, werden Füller-Kaufwert und Servicekosten neu aus den Ausgaben berechnet.

## Logik
- Kategorie `Füller` + verknüpfter Füller → zählt zum Kaufwert des Füllers.
- Kategorie `Service/Reparatur` + verknüpfter Füller → zählt zu Servicekosten des Füllers.
- Automatische Kauf-Einträge erhalten intern ein Tag `AUTO-PEN-PURCHASE:<id>`.
