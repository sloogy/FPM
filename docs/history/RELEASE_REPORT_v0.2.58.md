# Release Report v0.2.58 – Schreibproben & Enthusiasten-Labor

## Ergebnis

Die Version erweitert FPM gezielt für Füller-, Tinten- und Papier-Enthusiasten. Wichtigster Ausbau ist ein neues Schreibproben-Modul mit Scrivener-artiger Binder-Struktur.

## Neue Funktionen

- Neues Navigationsmodul „Schreibproben“.
- Neue Datenbanktabelle `writing_samples`.
- Schreibprobe verknüpfbar mit Füller, Tinte, Papier und Feder.
- Messwerte: Linienbreite, Trockenzeit, Feathering, Durchschlag, Shading, Sheen, Fluss, Feedback, Gesamtbewertung.
- Textprobe und Bild-/Scan-Pfad erfassbar.
- Binder-Gruppierung nach Füller, Tinte und Papier.
- Automatische Gruppen „Highlights“ und „Prüfen“.
- Logikdienst `logic/writing_sample_service.py` mit Tests.

## Releasefähigkeit

- Bestehende Daten werden nicht gelöscht.
- Neue Tabelle wird durch SQLAlchemy `create_all()` angelegt.
- Keine riskante direkte BudgetManager-Kopplung.
- Feature ist lokal/offline und passt zur bestehenden Architektur.

## Einschränkung

Der echte PySide6-GUI-Start konnte in der Sandbox nicht geprüft werden, wenn PySide6 nicht installiert ist. Die Source-Checks, Tests und i18n-Audits decken die neue Logik und statische Integrität ab.
