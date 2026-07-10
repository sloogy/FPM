# Changelog v0.2.83 – Search & Media Import Hardening

## Geändert

- Manuelle Füller-Datenrecherche nutzt jetzt Google-freundlichere Suchbegriffe.
- Hersteller-`site:`-Suche bleibt die erste Stufe, danach folgt offene Google-Suche; DuckDuckGo bleibt als Fallback und für den testbaren HTML-Parser erhalten.
- Bildsuche heißt nun klarer „Google-Bildsuche“ und öffnet kompaktere Suchanfragen.
- Kein langer URL-Block mehr im „Kein sicherer Treffer“-Dialog.

## Neu

- Neue zentrale Medienablage: `data/media/pens/<id>_<marke>_<modell>/`.
- Füllerbilder werden unter `images/` im jeweiligen Füllerordner importiert.
- Schreibprobenbilder werden unter `writing_samples/` im jeweiligen Füllerordner importiert.
- Lokale Bilddateien und direkte Bild-URLs werden beim Speichern kopiert; die Datenbank speichert nur den verwalteten Pfad.
- Neuer Service `logic/media_storage_service.py` mit testbarer Slug-/Import-/Ablagelogik.

## Behoben

- Lose Bildpfade außerhalb des Datenverzeichnisses werden bei neuen Imports vermieden.
- Schreibprobenbilder liegen nicht mehr ohne Zusammenhang in einem allgemeinen Feld, sondern beim Füller.
- Factory-Reset berücksichtigt nun auch Schreibproben-Bildpfade und die neue `media/`-Struktur.
- Kopieren eines Füllers nutzt beim Inline-Feder-Fallback wieder die Quelle statt einer noch nicht existierenden Zielvariable.

## Tests

- `tests/test_media_storage_service.py`
- Angepasste URL-Tests in `tests/test_pen_dimensions_service.py`
