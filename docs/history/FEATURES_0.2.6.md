# v0.2.6 – Service-/Sperrstatus, Tintenbasis, Federmaterial

## Neu

- Problemfüller / Service / Sperre direkt in der Füllerverwaltung.
- Sperrdauer mit Startdatum und Tagen, Standard 30 Tage.
- Gesperrte Füller werden aus Rotation und Einfüllen ausgeschlossen.
- Servicekosten werden automatisch als Ausgabe `Service/Reparatur` erfasst.
- Service-Sperre schließt aktive Tintenfüllung automatisch als gereinigt.
- Tintenstammdaten aus der Nutzer-Tabelle werden beim ersten Start automatisch angelegt.
- Tinten enthalten jetzt Farbtyp, Sheen-Level/-Farbe, Feathering, Shading, Fluss, Sättigung und Charakter-Notiz.
- Tinten können als leer markiert werden.
- Benutzte Tinten werden beim Löschen archiviert statt hart gelöscht, damit Historie erhalten bleibt.
- Leere/archivierte Tinten werden nicht mehr für Rotation oder Befüllen vorgeschlagen.
- Federmaterial ergänzt: Stahl, 14k, 18k, Titan usw.

## Datenbank-Migration

Die App erweitert bestehende SQLite-Datenbanken automatisch mit neuen Spalten. Bestehende Daten werden nicht gelöscht.
