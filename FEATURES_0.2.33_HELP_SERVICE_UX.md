# FountainPen Manager v0.2.33 – Help & Service UX

## Schwerpunkt
Diese Version ergänzt Erklärbarkeit und Service-/Sperren-Sichtbarkeit, damit die Regel- und Wartungslogik nicht nur technisch funktioniert, sondern im Alltag nachvollziehbar bleibt.

## Neu

### Zentrale Hilfe
- Neues Modul **Hilfe** in der Seitenleiste.
- Erklärungen für Schnellstart, Easy/Expert Mode, Full Auto Mode, Regelgruppen, Warnstufen, Verbrauch, Service und Glossar.
- Ziel: First-User-Experience verbessern und Regelentscheidungen verständlicher machen.

### Dashboard: Service & Sperren
- Neue Dashboard-Karte **Service/Sperren**.
- Neue Tabelle **Service & Sperren** mit:
  - Füller
  - Status
  - Grund
  - Bis / Tage
  - Aktionsempfehlung
- Zeigt Füller im Service, Problemfüller, manuelle Sperren und kritische Austrocknungs-/Reinigungsrisiken.

### Service-Ende per Datumsauswahl
- Service-/Sperrdialog ergänzt um:
  - Startdatum
  - Dauer
  - geplantes Enddatum
  - Option „ohne Enddatum / manuell entsperren“
- Dauer und Enddatum synchronisieren sich gegenseitig.

### Austrocknungsrisiko als Sperrstatus
- Neuer Status `dry_risk` / **Austrocknungsrisiko**.
- Wird in Füllerliste, Detailansicht, Rotation und Dashboard berücksichtigt.
- Rotation und Full Auto überspringen diesen Status.

## Stabilität
- Schema-Version auf `0.2.33` gesetzt.
- Syntaxcheck: OK.

## Hinweis
Ein vollständiger UI-Runtime-Test konnte in der Build-Umgebung nicht ausgeführt werden, weil PySide6 dort nicht installiert ist. Der Python-Syntaxcheck und die interne Strukturprüfung sind erfolgreich.
