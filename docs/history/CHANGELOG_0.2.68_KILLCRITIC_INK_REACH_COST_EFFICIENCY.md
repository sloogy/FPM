# Changelog 0.2.68 – KILLCRITIC Ink Reach & Cost Efficiency

**Datum:** 6. Juli 2026
**Build:** killcritic-ink-reach-cost-efficiency
**Basis:** v0.2.67 KILLCRITIC Reference Images / Filldata

## Neu

### Tintenreichweite & Kosten-Effizienz (`logic/ink_reach_service.py`)
Neues reines Logikmodul, das die vorhandene Füll-Historie (`InkLoad.volume_ml`,
`loaded_date`) je Tinte zu zwei Sichten verdichtet:

**Enthusiast-Sicht – „Wie lange reicht die Flasche?"**
- Geschätzte verbleibende Füllungen (Rest ÷ Ø-Füllmenge)
- Verbrauchsrate pro Tag über das beobachtete Zeitfenster
- Voraussichtliches Leerdatum (Prognose)
- Ø-Füllmenge und Anzahl real erfasster Füllungen

**Sammler-Sicht – „Wie wirtschaftlich ist die Flasche?"**
- Kosten pro ml (Kaufpreis ÷ Flaschengröße)
- Kosten pro Füllung (Kosten pro ml × Ø-Füllmenge)
- Bereits verbrauchter Geldwert und verbleibender Wert
- Aggregat `collection_ink_value_summary()`: verbrauchter/verbleibender
  Sammlungswert, wirtschaftlichste und teuerste Tinte, gemischte Währungen
  werden als `mixed` gemeldet (keine falsch summierten Beträge)

### UI-Anbindung
- Im Tinten-Detail erscheinen die neuen Kennzahlen als kompakte Zeilen,
  farblich nach Status (`reorder_soon` orange, `healthy` grün, sonst grau).
- Es wird nur angezeigt, was real belegt ist. Ohne Füll-Historie oder ohne
  Preis-/Größenangabe bleiben die Zeilen aus – nichts wird geraten.

## Design-Grundsätze
- Grundlage sind ausschließlich `InkLoad`-Einträge mit positivem Volumen;
  0-/None-Füllungen werden ignoriert.
- Verbrauchsrate/Leerdatum werden erst ab ≥ 14 Tagen Beobachtung ausgewiesen,
  um Scheingenauigkeit zu vermeiden.
- Kein Schreibzugriff, keine Mutation – dadurch ohne DB/GUI-Runtime testbar.

## Hardening / Bereinigt
- Toter, veralteter i18n-Wert `app.version` (stand auf `v0.2.62`, wurde nirgends
  aufgerufen) auf den aktuellen Release-Stand synchronisiert. Die echte
  Versionsanzeige nutzt weiterhin `app_info.app_version_label()`.
- Release-Metadaten- und Installer-Guard-Tests auf 0.2.68 nachgezogen.

## Migration
Keine strukturelle DB-Migration nötig. `SCHEMA_VERSION` wird konsistent auf
0.2.68 gehoben (idempotenter AppSetting-Marker, keine Startschranke).

## Geänderte/neue Dateien
- `logic/ink_reach_service.py` (neu)
- `tests/test_ink_reach_service.py` (neu)
- `ui/ink_widget.py`
- `i18n/de.json`, `i18n/en.json`, `i18n/fr.json` (+11 Keys → 1892 × 3)
- `database/db.py` (SCHEMA_VERSION)
- `app_info.py`, `version.json`, `VERSION_INFO.txt`
- `latest.json.template`, `docs/latest.json.template`
- `installer/FountainPenManager_Setup.iss`
- `tests/test_release_hardening_static.py`, `tests/test_windows_packaging_static.py`
