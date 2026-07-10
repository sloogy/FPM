# FountainPen Manager v0.2.20 – halbgelöste Punkte weiter geschlossen

Basis: `fpm v0.2.19 all fixes.zip`

## Umgesetzt

### 1. Money/Currency am Objekt
- `Pen`: `purchase_currency`, `market_currency`, `insurance_currency`, `service_currency`
- `Ink`: `purchase_currency`
- `Paper`: `purchase_currency`
- Dashboard rechnet nicht mehr nur über geratenen Expense-Fallback, sondern nutzt die Currency-Felder am Objekt.

### 2. Dashboard aktiv/archiviert getrennt
- Dashboard nutzt für aktive Karten und Safety Timer nur `Pen.is_active=True`.
- Archivierte Füller stören normale Safety-/Aktiv-Statistiken nicht mehr.
- Tooltip der Füller-Karte zeigt aktive und archivierte Füller getrennt.

### 3. Migration/Backup
- Vor Schema-Migrationen wird ein Tagesbackup unter `~/.fpm_data/migration_backups/` angelegt.
- `schema_version` wird in `AppSettings` auf `0.2.20` gesetzt.
- Neue Currency-Spalten werden per Migration ergänzt.

### 4. Region/Währung in Eingabe und Anzeige
- Füller-, Tinten- und Papierdialoge besitzen Currency-Auswahl für Kauf-/Wertfelder.
- Euro-Hardcoding in den Preisfeldern wurde ersetzt durch die Standardwährung aus den Einstellungen.
- Detailanzeigen verwenden `format_money()` statt festem `€`.
- Servicekosten verwenden die Einstellungswährung.

### 5. Ausgaben-Sync sauberer
- Füller-Kaufpreis und Servicekosten aus Expenses werden in die Standardwährung umgerechnet, statt Fremdwährungen ungeprüft zu summieren.
- Papier-Auto-Expenses übernehmen die Currency des Papierobjekts.
- Füller-Auto-Expenses übernehmen die Currency des Füllerobjekts.

### 6. Farbfamilien-Aliase zentralisiert
- Neues Modul `logic/color_family_service.py`.
- Deutsch/Englisch/Synonyme wie `dunkelblau`, `navy`, `königsblau`, `türkis`, `petrol`, `bordeaux` werden normalisiert.
- CSV-Import und Rotation nutzen dieselbe Normalisierung.

### 7. CSV-Import weniger still
- Pen-/Ink-Import übernehmen Currency-Felder aus CSV, falls vorhanden.
- Nicht erkannte Kaufdaten werden im Importbericht gemeldet statt komplett still geschluckt.

## Weiter offen / bewusst nicht vollständig gelöst

- Echter Wizard mit klickbaren CTA-Buttons.
- Vollständiger Import-Preview-Dialog vor dem Speichern.
- Papier beeinflusst Rotation noch nicht fachlich.
- Medienmodell mit mehreren Bildern pro Objekt fehlt weiterhin.
- Undo/EventLog ist noch nicht eingeführt.
- i18n-Abdeckung ist weiterhin nicht vollständig.

## Testhinweis

In dieser Umgebung war kein SQLAlchemy installiert, daher wurde Syntax per `compileall` geprüft, aber kein echter DB-Starttest ausgeführt.
