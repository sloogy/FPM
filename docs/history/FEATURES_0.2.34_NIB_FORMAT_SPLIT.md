# v0.2.34 – Trennung Format/Standard vs. Exemplar bei Federn

Basis: v0.2.33-help-service-ux

Auslöser: zwei nominell gleiche Federn (z.B. zwei Bock #6 EF) sind in der Realität
unterschiedlich – getunt, anderer Feed, anderes Schreibgefühl. Bisher hat der
Füller-Dialog beim Speichern beim Anlegen einer „neuen" Feder via Marke+Feinheit
gesucht und auf das Duplikat zusammengeführt. Das war ein halber Bug: die Engine
ignorierte ausgerechnet die Felder, die Exemplare unterscheiden.

## Neues Datenmodell
**`NibFormat`** (neue Tabelle): Format/Standard einer Feder – Marke, Baugröße,
proprietär, kompatible Füller, Format-Notiz. Bestimmt **Kompatibilität**
(passt in Jinhao x750 etc.) und wird zwischen Exemplaren geteilt.

**`Nib`** (erweitert): das einzelne Exemplar. Verweist über `format_id` auf
ein NibFormat. Neue Felder:
- `source` – Bezug / Tuner (z. B. Gravitas, FNF, Nibsmith, Shop)
- `feed_type` / `feed_notes` – Tintenleiter (Standard, Ebonit, Custom + freie Beschreibung)
- `stiffness_level` (1–5) – sehr weich/flex … sehr steif
- `tuning_notes` – was wurde getunt, von wem
- `label` – Spitzname zur Unterscheidung

Legacy-Spalten (`manufacturer`, `physical_size`, `is_proprietary`) bleiben
bestehen und werden synchron gehalten, damit alter Code nicht bricht.
`Nib.effective_manufacturer / effective_physical_size / effective_is_proprietary`
liefern den Wert aus dem Format (mit Legacy-Fallback). `Nib.display_label`
baut einen sprechenden Namen inkl. Bezug für die Anzeige.

## Bugfix: kein Auto-Merge mehr auf (Marke, Feinheit)
`_resolve_nib` im Füller-Dialog (`pen_widget.py`):
- **Vorher:** suchte bei „neuer" Feder nach Marke+Feinheit, bot Verschmelzen an.
  → Gravitas-Bock und Standard-Bock wurden zusammengeführt.
- **Jetzt:** jedes Exemplar ist eigenständig. Nur das **Format** wird dedupliziert
  (Marke + Baugröße + proprietär) – Kompatibilitätsdaten liegen einmal,
  Schreibgefühle bleiben getrennt.

## Migration für bestehende DBs
- ALTER TABLE über das vorhandene `_migrate_schema`-Muster fügt die neuen
  Spalten an `nibs` an und legt `nib_formats` an (über `create_all`).
- Neue Funktion `_migrate_nib_formats()` läuft beim Start: erzeugt aus den
  bestehenden Federn pro `(Marke, Baugröße, proprietär)`-Tupel ein NibFormat
  und setzt `format_id` auf den vorhandenen Federn.
- Vorhandene `is_flexible=True` wird in `stiffness_level=2` übersetzt (sofern
  der Default 4 noch nicht überschrieben wurde). Idempotent.
- `schema_version` → `0.2.34`.

Verifiziert per Raw-SQLite-Test:
- 2 bestehende „Bock #6 EF" teilen sich nach Migration EIN Format, bleiben aber
  2 getrennte Exemplare.
- Eine weitere Bock #6 EF, frisch über den Assistenten angelegt, wird als
  3. eigenständiges Exemplar gespeichert.

## UI-Änderungen
- **`NibDialog`** (Feder-Modul): in zwei Bereiche gegliedert – „Format &
  Kompatibilität" mit Picker (vorhandenes Format wählen oder neu anlegen) und
  „Exemplar / Schreibgefühl" mit allen neuen Feldern. Format-Felder werden
  bei gewähltem Format gesperrt (kommen aus dem Format), bei neuem Format
  editierbar.
- **Füller-Dialog „🔧 Feder"** (Inline-Assistent): zusätzlich Bezug / Tuner,
  Steifigkeit (1–5) und Spitzname. Bestehende Felder unverändert.
- **Feder-Tabelle**: zwei neue Spalten Bezug + Steifigkeit; Marke/Baugröße
  zeigen die effektiven Format-Werte.
- **Füller-Tabelle & Detail-Panel**: Feder zeigt `display_label` inkl. Bezug;
  Detail-Panel zusätzlich Bezug, Nibmeister, Steifigkeit, Feed, Tuning,
  Format-Kompatibilität.

## Regel-Engine
`_nib_text` zieht jetzt effektive Format-Werte und nimmt zusätzlich Bezug,
Spitzname und abgeleitetes „flex" (aus `stiffness_level ≤ 2`) ins Suchtext-
Feld auf. Bestehende Regeltypen funktionieren unverändert.

## Bewusst nicht angepasst
- `wishlist_widget.Nib(manufacturer=…)` beim Übernehmen aus der Wishlist:
  legt weiterhin direkt eine Nib mit Legacy-Feldern an; das Format wird beim
  nächsten Start durch `_migrate_nib_formats` automatisch ergänzt.
- `expenses_widget` zeigt Federn weiterhin als `manufacturer size` – läuft
  über die Legacy-Spalten und bleibt korrekt.
