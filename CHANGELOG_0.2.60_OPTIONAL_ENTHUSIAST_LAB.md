# FPM v0.2.60 – Optionales Enthusiasten-Lab

## Neue optionale Sammlerfunktionen

- Tinten-Restmengen mit Status: OK, niedrig, Nachkauf prüfen, leer, unbekannt.
- Schreibproben-Vergleichsansicht als Grid für zwei bis vier Proben.
- Feder-Tausch-Historie pro Füller auf Basis der vorhandenen Pen-Nib-Setups.
- Farbfamilien-Lückenanalyse mit Empfehlungen wie warmes Braun, kühles Grau oder Business-Blau.
- Reinigungsprotokoll mit Dauer, Aufwand, Spülgängen, Reiniger, Ergebnis und Statistik pro Tinte.

## DAU-Schutz

- Keine Pflichtfelder für Enthusiasten-Daten.
- Normale Inventar-, Tinten- und Schreibprobenflüsse bleiben unverändert.
- Reinigungsprotokoll ist zusätzlich zum einfachen "gereinigt"-Status.

## i18n

- Neue UI-Texte vollständig in Deutsch, Englisch und Französisch ergänzt.

## Technik

- Neues Modul `logic/enthusiast_lab_service.py`.
- Neues UI-Modul `ui/enthusiast_lab_widget.py`.
- Neue DB-Tabelle `cleaning_logs`.
- Zusätzliche optionale Felder für Tinten-Nachkauf und Feder-Setup-Notizen.
