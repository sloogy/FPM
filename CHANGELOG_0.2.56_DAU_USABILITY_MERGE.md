# v0.2.56 – DAU-Usability-Merge & offene Release-Punkte

Basis: v0.2.55 (GitHub Release Hardening). Diese Version schließt die bei der
Release-Prüfung von v0.2.55 gefundenen offenen Punkte und merged das in diesem
Zweig fehlende v0.2.53/v0.2.54-Paket.

## Behoben (offene Punkte aus v0.2.55)
- Status-Untermenü „Gekauft" startet jetzt die nachvollziehbare Übernahme
  (vorher nur Infobox); Untermenü-Eintrag wieder sichtbar.
- Neuanlage eines Wunsches direkt mit Status „Gekauft" startet die Übernahme
  (vorher stiller bought-Eintrag ohne Sammlung/Ausgabe).
- Erfolgsmeldung nach jeder Übernahme (verdrahtet transfer_done_*-Keys;
  neuer Key wishlist.transfer_expense_body).
- settings_widget.py: halb übersetzter f-String „UI-Skalierung gespeichert…"
  auf echten Key settings.ui_scale_saved_body umgestellt (Regression aus v0.2.53).
- tools/i18n_visible_text_audit.py wiederhergestellt (case-insensitive
  Deutsch-Erkennung, Bridge-Aufrufstellen, logic/-Scan, _mk_btn-Helper).

## Gemergt (v0.2.54 Usability/DAU-Paket)
- Wishlist: Buttonleiste (Bearbeiten / Als gekauft übernehmen / Löschen),
  Suchfeld (an globale Suche angebunden), Statusfilter mit Default
  „Aktive Wünsche".
- Füller: einheitliches EmptyStateWidget statt In-Tabellen-Hinweis.
- Tastatur: Ctrl+N (neuer Eintrag), Ctrl+F (Suche), Ctrl+1–9 (Navigation),
  Entf (Löschen, nur bei fokussierter Tabelle).
- Bilder: Drag & Drop auf die Füllerseite; Klick auf Detailbild öffnet
  ImageZoomDialog (Briefing-Anforderungen „Drag & Drop" und „Große
  Bilderansicht").
- ui/theme.py: fünf zentrale Button-Stilkonstanten, mechanisch migriert.
- Tooltips: Transfer-Button, Detailbild, globales Suchfeld (inkl. Ctrl+F-Hinweis).

## Validierung
- python -m compileall -q . ✅
- 49/49 Tests ✅ (Headless-Shim)
- i18n_audit / quality / key_wiring / runtime / visible_text ✅ (1538 Keys × 3)
- Transfer-Harness: Kontextmenü- und Status-Untermenü-Pfad erzeugen Pen +
  Expense + Status „gekauft" + Erfolgsmeldung ✅

## Nicht automatisch geprüft (vor Final-Release erforderlich)
- GUI-Start mit PySide6; Shortcuts, Drag & Drop, Zoom, Filter sind Laufzeitverhalten
- Datenbankmigration mit bestehenden Nutzer-Datenbanken
- Sprachwechsel visuell in DE/EN/FR
- Paketbau als ausführbare Anwendung
