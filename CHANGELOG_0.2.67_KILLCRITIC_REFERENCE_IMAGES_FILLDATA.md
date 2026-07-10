# Changelog 0.2.67 – KILLCRITIC Reference Images & Fill Data Hardening

Release-Kandidat auf Basis v0.2.66 gehärtet und auf v0.2.67 angehoben.

## Neu

- Füller-Referenzcache erweitert: Neben Dimensionen können jetzt auch Füllsystem, Füllvolumen und Bild-URLs hinterlegt werden.
- Füller-Dialog: zusätzlicher Button **Bild suchen** direkt beim Bildfeld.
- Füller-Dialog: **Füller-Daten suchen** übernimmt Cache-Treffer per Bestätigung in leere/unberührte Felder.
- Direkte Bild-URLs im Bildfeld werden beim Speichern, sofern erreichbar, lokal nach `data/images/pens/` kopiert.
- Bildsuche und technische Datensuche werden ohne Treffer getrennt geöffnet, damit der Nutzer Hersteller-/Shopdaten prüfen kann.
- Beispielcache ergänzt: `docs/pen_reference_cache_example.json`.

## Gehärtet

- Keine automatische Fremdseiten-Scraping-Logik im Release-Pfad.
- Keine blinde Überschreibung gepflegter Sammlerdaten.
- Füllsystem-Aliasse werden normalisiert, z. B. `Kolben` → `piston`, `cartridge/converter` → `converter`, `vacuum filler` → `vac`.
- Bild-Import begrenzt Downloads auf 8 MB und akzeptierte Bildendungen.
- Referenzcache ignoriert kaputte/unsichere Zeilen statt die App zu blockieren.

## Tests

- Neue Regressionstests für Füllsystem-/Kapazitäts-/Bild-Referenzdaten.
- Neue Regressionstests für Bildsuch-URLs und Füllsystem-Normalisierung.
- Version, Installer und i18n-Audits auf v0.2.67 nachgeführt.
