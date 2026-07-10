# v0.2.47 – i18n Release Candidate Hardening

## Übersetzungen
- Gemischte DE/EN/FR-Übersetzungen in EN/FR korrigiert.
- Navigationsmodul auf stabile `nav.*` Keys umgestellt.
- Sichtbare Enum-/Listenwerte für Ausgaben, Zahlungsarten, Papierarten, Wishlist-Typen/-Status und Regelgruppen übersetzbar gemacht.
- Settings- und Hilfe-Seite über Legacy-Exact-Mappings gegen halb übersetzte Texte gehärtet.
- Pen-/Rotation-Detailtexte über `translate_source_text()` abgesichert.
- Fehlende Keys ergänzt und alle Sprachdateien auf gleiche Struktur gebracht.

## Checks
- `compileall` erfolgreich.
- i18n-Struktur-Audit erfolgreich.
- i18n-Quality-Audit erfolgreich.
- i18n-Key-Wiring-Audit erfolgreich.
- i18n-Runtime-Audit erfolgreich.
- Zusatzcheck: alle direkten `t("...")` Keys existieren in `de.json`.

## Hinweis
Ein echter GUI-Smoke-Test mit PySide6/SQLAlchemy muss lokal noch ausgeführt werden.
