# FPM v0.2.22 stable-merge

Basis: v0.2.20 halbgelöste Fixes.
Selektiv übernommen aus v0.2.21: UX-Verbesserungen, Archiv-Karte, Why-Score-Dialog, EmptyStateWidget, leere Federliste.

## Bewusst beibehalten aus v0.2.20
- `LocaleService` und `format_money()` statt harter Euro-/CHF-Anzeigen.
- Currency-Felder und Service-Currency im Datenmodell.
- `color_family_service.py` mit Farbfamilien-Normalisierung.
- funktionierende `rule_engine.py` ohne Einrückungsfehler.
- Migration/Backup-Logik aus v0.2.20.

## Korrigiert
- App-Version auf `0.2.22-stable-merge` gesetzt.
- `rotation_engine.py` importiert `normalize_color_family` explizit.
- Rotationsvorschläge liefern Score-Komponenten für den Why-Score-Dialog.
- Dashboard zählt aktive und archivierte Füller getrennt.
- `MIT TINTE` zählt nur aktive, verfügbare, nicht blockierte Füller.
- `rotation_widget.py` zeigt Why-Score beim Klick auf die Score-Spalte.

## Bewusst noch nicht umgesetzt
- Papier in Rotation.
- Media-Modell.
- Undo/EventLog.
- Vollständige i18n.
- vollständige Import-Preview-Migration aus v0.2.21, weil diese dort Währungslogik zurückbaut und erst sauber neu integriert werden sollte.
