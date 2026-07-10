# Changelog 0.2.66 – KILLCRITIC Collector Dimensions Hardening

## Status
Release-Kandidat auf Basis v0.2.65 gehärtet und auf v0.2.66 angehoben.

## Geändert
- Rotationslogik gehärtet: Bereits aktiv genutzte Tinten werden standardmäßig nicht erneut für andere Füller vorgeschlagen.
- Fixe Füller-Tinten-Zuordnungen bleiben weiterhin erlaubt und überschreiben die Dubletten-Sperre.
- Neue AppSetting-Option `rotation_allow_active_ink_duplicates=0` als Default, damit Power-User die Regel später bewusst übersteuerbar machen können.
- Ink-Verbrauch beim Befüllen nutzt jetzt zentral `apply_ink_consumption()` statt verstreuter Sonderlogik.
- Tinten-Restmenge wird zuverlässig auf `0.0` begrenzt; leere Tinten werden als leer markiert.

## Neu
- Neuer servicebasierter Füller-Dimensions-Lookup: `logic/pen_dimensions_service.py`.
- Lokaler Dimensions-Cache über JSON-Datei, bewusst offlinefähig und ohne harte Internet-Abhängigkeit.
- Browsergestützte Recherche-URLs für Marke/Modell, falls keine lokalen Maße vorhanden sind.
- Button „Maße suchen“ im Füller-Dialog.
- Gefundene Maße füllen nur leere Felder und überschreiben vorhandene Nutzerangaben nicht automatisch.
- Mehrsprachige UI-Texte für Deutsch, Englisch und Französisch ergänzt.

## Tests
- Neue Tests für Dimensions-Service, Normalisierung, Cache-Matching und Recherche-URLs.
- Statische Regressionstests für aktive-Tinten-Dubletten und zentrale Verbrauchslogik.
- Testumfang: 93 grüne Tests.

## Build/Release
- Version synchronisiert: `0.2.66`.
- Schema-Version synchronisiert: `0.2.66`.
- Windows-Release-Dokumente auf `0.2.66` aktualisiert.
- Build-Label: `killcritic-collector-dimensions-hardening`.
