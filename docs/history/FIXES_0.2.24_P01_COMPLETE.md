# FPM v0.2.24 – P0/P1 vollständig abgeschlossen

Basis: v0.2.23-p01-rule-engine

## P0 – Blocker

### P0.1 · Servicekosten hardcoded € behoben
`pen_widget.py`: Servicekosten-Detailzeile nutzt jetzt `format_money(service_cost, service_currency)`
statt dem hardcodierten `f"€ {:.2f}"`.

### P0.2 · service_currency Combo im Service-Dialog
Service-Dialog hat jetzt ein Währungs-Combo (CHF/EUR/USD/GBP) neben dem Kosten-Feld.
`get_data()` liefert `currency` zurück; `pen_widget._block_pen()` übernimmt sie korrekt.

### P0.3 · Currency-Felder auf Optional[str] ohne Default
`database/models.py`: Alle 6 Currency-Felder (Pen: purchase/market/insurance/service,
Ink: purchase, Paper: purchase) sind jetzt `Optional[str]` ohne DEFAULT.
Neue Objekte bekommen keine implizite Währung – die UI fragt explizit oder nutzt LocaleService
als bewussten Fallback.

### P0.4 · DB-Migration ohne DEFAULT 'CHF'
`database/db.py`: Migration legt Currency-Spalten mit `VARCHAR(3)` ohne DEFAULT an.
Bestehende NULL-Werte bleiben NULL (unterscheidbar von explizit gesetztem "CHF").
Schema-Version auf `0.2.24` gesetzt.

## P1 – Usability

### P1.1 · ui/common.py: ImportPreviewDialog zentralisiert
Neues Widget `ImportPreviewDialog` in `ui/common.py`.
Zeigt Validierungsbericht (✅ OK / ⚠️ Warnung / ❌ Fehler) vor jedem Import.
Nutzer bestätigt explizit bevor Daten gespeichert werden.

### P1.2 · ink_widget: ImportPreviewDialog eingebaut
`_import_inks()` führt Zweiphasen-Import durch:
1. Validierungsdurchlauf → Preview-Dialog
2. Nur bei Bestätigung → importieren
CSV-Fehlerzeilen werden übersprungen, nicht mehr still verworfen.
`purchase_currency` wird aus CSV übernommen.

### P1.3 · EmptyStateWidget konsequent (QStackedWidget-Pattern)
`nib_widget.py`, `ink_widget.py`, `paper_widget.py` nutzen jetzt alle ein echtes
`EmptyStateWidget` mit passendem Icon, Text und CTA-Button statt inline Table-Boilerplate.
Jedes Widget hat einen `QStackedWidget` mit Tabelle (Index 0) und EmptyState (Index 1).

### P1.4 · Grail-Pen-Schutz als Standard-Regelkonfiguration
`database/db.py`: 5 Standard-Regeln werden beim ersten Start (leere Rules-Tabelle) automatisch angelegt:
- Grail Pen + Shimmer → BLOCKED
- Grail Pen + Pigment → BLOCKED
- Vac + Shimmer → CRITICAL
- EF-Feder + trockene Tinte → WARNING
- Vintage + hoher Reinigungsaufwand → WARNING

Regeln sind sofort aktiv, vollständig editier- und deaktivierbar im Regeln-Widget.

### P1.5 · WhyScoreDialog ProgressBar normiert
Balken skaliert jetzt auf 0-100 normiert (Divisor 1.5, max. Erwartungswert 150).
Extreme Werte wie rule_delta=-220 zeigen jetzt einen proportionalen Balken
statt immer 100% zu füllen. Exakter Wert bleibt im Balken-Label sichtbar.

## Bewusst zurückgestellt (P2/P3)
- Papier in Rotation
- Media-Modell (mehrere Bilder)
- Undo/EventLog
- Vollständige i18n
- AppEventBus (Session-Race)
- Onboarding-Wizard (4-Schritt)
