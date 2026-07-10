# Changelog 0.2.77 – Quick Actions & Mode-Logic Hardening

**Datum:** 7. Juli 2026
**Build:** quick-actions-mode-logic-hardening
**Basis:** v0.2.76 (Simple Mode / Expert Area)

## Behoben

### Stumme Schnellaktionen „Befüllen" / „Reinigen" (DAU-kritisch)
Die zwei wichtigsten Einfachmodus-Buttons (Dashboard **und** Toolbar) riefen
`_load_ink()` / `_mark_cleaned()` auf, die bei fehlender Tabellen-Selektion
kommentarlos abbrachen – für Einsteiger wirkten die Buttons tot.

**Fix:** Neuer gemeinsamer Helfer `PenWidget._quick_pen_id()`:
- Vorhandene Selektion wird wie bisher verwendet (kein Verhaltensbruch).
- Existiert **genau ein aktiver Füller**, wird er automatisch gewählt –
  der typische Einsteiger mit einem Füller kommt ohne Klickumweg ans Ziel.
- Sonst erscheint ein freundlicher Hinweis („Bitte zuerst einen Füller in der
  Liste auswählen …", DE/EN/FR) statt Stille.

### Übersehener Versions-Pin
`tests/test_killcritic_release_ui_audit_0275_static.py` pinnt Version und
README-Dateiverweise – beim Bump nachgezogen; die README-Links zeigen jetzt
auf die real existierenden 0.2.77-Dokumente. (Der 0275-Guard hat damit exakt
die Fehlerklasse gefangen, für die er gebaut wurde.)

## Neu: funktionale Modus-Tests
`tests/test_quick_actions_and_mode_logic_0277.py` ergänzt die statischen
0276-Checks um **ausführbare** Logik (headless):
- `fallback_page()`: alle versteckten Expertenseiten → Dashboard, Kernseiten
  bleiben, Expertenmodus leitet nie um.
- `page_visible()` deckungsgleich mit `SIMPLE_PAGES`.
- `normalize_app_mode()` defensiv (None/Groß-/Fremdwerte → simple).
- Partition: `SIMPLE_PAGES ∪ EXPERT_ONLY_PAGES` = alle 14 Module, disjunkt;
  Simple-Sidebar zeigt exakt `SIMPLE_PAGES` (AST-basiert, ohne Qt-Import).
- Guards für den Schnellaktions-Fix inkl. i18n-Schlüssel in allen Sprachen.

## i18n
+2 Keys × 3 Sprachen (`ui.pen_widget.quick_no_selection_title`,
`ui.pen_widget.quick_select_pen_hint`) → 1974 × 3.

## Geänderte/neue Dateien
- `ui/pen_widget.py` (Helfer + zwei Methodenköpfe)
- `i18n/de.json`, `i18n/en.json`, `i18n/fr.json`
- `tests/test_quick_actions_and_mode_logic_0277.py` (neu)
- `tests/test_killcritic_release_ui_audit_0275_static.py` (Pins)
- `README.md` (Dokument-Links), `app_info.py`, Versions-/Template-Dateien
- übliche Pin-Tests (`release_hardening`, `windows_packaging`, …)
