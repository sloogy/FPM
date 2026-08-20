# FPM v0.2.61 – Kontextnahe Enthusiasten-Härtung

Dieser Release behält v0.2.60 als stabile Basis und übernimmt die besten UX-Ideen aus der alternativen v0.2.59-Enthusiastenlinie, ohne deren riskante Doppelmodelle zu importieren.

## Neu / verbessert

- Füller-Detailansicht mit direkten Enthusiasten-Aktionen:
  - Schreibprobe zu diesem Füller hinzufügen
  - Schreibproben dieses Füllers vergleichen
  - Federhistorie anzeigen
  - Feder-/Setup-Daten bearbeiten
- Tinten-Detailansicht mit Füllstand-Ampel und Nachkauf-Empfehlung.
- Schreibproben-Dialog kann mit vorausgewähltem Füller/Tinte/Papier/Feder geöffnet werden.
- Release-ZIP wird ohne Cache-Artefakte gepackt.

## Bewusst nicht übernommen

- Keine zweite Federhistorie-Tabelle `nib_change_events`.
- Keine Tintenverbrauchslogik beim Reinigen. Verbrauch bleibt am Befüllen/Bestandspflege orientiert.

## Migration

- Schema-Version auf `0.2.61` gehoben.
- Bestehende v0.2.60-Datenbanken bleiben kompatibel.
