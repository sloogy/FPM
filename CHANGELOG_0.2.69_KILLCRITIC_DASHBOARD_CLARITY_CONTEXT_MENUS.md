# Changelog 0.2.69 – KILLCRITIC Dashboard Clarity & Context Menus

**Datum:** 6. Juli 2026
**Build:** killcritic-dashboard-clarity-context-menus
**Basis:** v0.2.68 KILLCRITIC Ink Reach & Cost Efficiency

## Schwerpunkt dieser Runde
Zwei ausdrücklich gewünschte Punkte: **Dashboard/UI übersichtlicher** und
**fehlende Rechtsklick-Optionen** ergänzen.

## Dashboard aufgeräumt

- **Leere Abschnitte werden ausgeblendet.** Safety-Timer, Service/Sperren,
  Sammlungs-Advisor und „Letzte Einfüllungen" erscheinen nur noch, wenn sie
  tatsächlich Inhalt haben. Ein gesundes, ruhiges Setup zeigt kein leeres
  Tabellen-Gerüst mehr.
- **„Alles im grünen Bereich"-Status.** Sobald Inventar existiert und weder
  Warnungen noch Service noch Advisor-Hinweise offen sind, erscheint ein
  kompakter grüner Hinweis statt mehrerer leerer Blöcke.
- Konsistent mit dem bereits vorhandenen Verhalten für Onboarding- und
  Budgetziel-Panel (die schon datengetrieben ein-/ausgeblendet wurden).

## Neue Rechtsklick-Menüs

- **Dashboard-Tabellen** (Safety-Timer, Service, Advisor, Aktivität):
  - „Zum Füller springen" / „Zur Tinte springen" (Sprung-Navigation)
  - „Details kopieren" (Zeile in die Zwischenablage)
  - „Aktualisieren"
- **Schreibproben-Liste:** Neu / Bearbeiten / Auswahl vergleichen / Löschen –
  nutzt die bestehenden, getesteten Aktionen; Einträge werden je nach Auswahl
  aktiviert/deaktiviert.
- **Enthusiast-Lab (Tinten-Restmengen):** „Zur Tinte springen",
  „Restmenge bearbeiten", „Details kopieren".

## Technische Umsetzung
- Neues Signal `navigate_to = Signal(int)` in Dashboard und Enthusiast-Lab.
  Das Hauptfenster verbindet es automatisch mit `_navigate` – nach demselben
  Muster wie das bestehende `tour_requested`-Signal, also ohne feste Kopplung.
- Kontextmenüs folgen exakt dem etablierten Muster der übrigen Listen
  (`setContextMenuPolicy` + `customContextMenuRequested` + `menu.exec(...)`).
- **Kritischer Guard:** Nach `menu.exec()` wird auf `None` geprüft, damit das
  Verwerfen des Menüs bei optionalen (ggf. `None`-)Aktionen nicht
  versehentlich eine Navigation auslöst.

## Tests
- Neuer statischer Guard-Test `tests/test_ui_context_menus_static.py`
  (7 Tests, GUI-frei) sichert Signal, Kontextmenü-Verdrahtung,
  Abschnitts-Sichtbarkeit, den None-Guard und die i18n-Kontext-Keys ab.
- Gesamt: 110 Logik-/Guard-Tests grün (der SQLAlchemy-abhängige
  Migrationstest läuft in der echten Dev-/CI-Umgebung).

## i18n
- +5 Keys (`dashboard.all_clear`, `dashboard.context.*`) → 1897 × 3.
- Schreibproben- und Enthusiast-Lab-Menüs verwenden bestehende Keys wieder.

## Migration
Keine strukturelle DB-Migration nötig. `SCHEMA_VERSION` konsistent auf 0.2.69.

## Geänderte/neue Dateien
- `ui/dashboard_widget.py`
- `ui/writing_samples_widget.py`
- `ui/enthusiast_lab_widget.py`
- `ui/main_window.py`
- `i18n/de.json`, `i18n/en.json`, `i18n/fr.json`
- `tests/test_ui_context_menus_static.py` (neu)
- `database/db.py` (SCHEMA_VERSION)
- `app_info.py`, `version.json`, `VERSION_INFO.txt`
- `latest.json.template`, `docs/latest.json.template`
- `installer/FountainPenManager_Setup.iss`
- `tests/test_release_hardening_static.py`, `tests/test_windows_packaging_static.py`
