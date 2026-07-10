# Changelog v0.2.87 – RELEASE AUDIT & MEDIA HARDENING

Ergebnis einer tiefen kritischen Release-Analyse (Volltext: `RELEASE_ANALYSE_v0.2.87_KRITISCH.md`).

## 🔴 Kritisch behoben: Datenverlust durch fehlgeschlagenen Bild-Import
`import_pen_image()` / `import_writing_sample_image()` liefen **innerhalb der offenen Transaktion vor dem Commit**. Jede Exception (Download-Timeout, Netzfehler, „Bilddatei ist zu groß" > 15 MB, leere Antwort, fehlende Schreibrechte) landete im generischen `except` → Rollback bzw. kein Commit. **Der komplett eingetippte Füller bzw. die Schreibprobe ging verloren, weil ein kosmetischer Bild-Import scheiterte.**

Jetzt:
- Import in `try/except` gekapselt, Fehler wird gemerkt statt geworfen.
- Der ursprüngliche Pfad/die URL bleibt am Datensatz erhalten.
- Der Commit läuft durch; **nach** dem Commit erscheint eine Warnung mit konkretem Grund (`media.import_failed_title/body`, DE/EN/FR).
- Betroffen und gefixt: `pen_widget._add`, `_edit_pen_by_id`, `_copy_pen`; `writing_samples_widget._add`, `_edit`.

## 🟠 Behoben: Die Recherche-„Kaskade" öffnete nur eine Stufe
Der Dialog „Kein sicherer Treffer" öffnete ausschließlich `search_urls[0]` und `image_search_urls[0]`, während `_open_pen_image_search()` zwei URLs öffnete – zwei Pfade, zwei Verhalten. Die fachlich wichtige zweite Stufe (bei Maßen die Herstellerseite, bei Bildern der KI-Prompt) wurde berechnet und verworfen. Die 0.2.86-Umstellung „KI zuerst" war dadurch faktisch eine *Ersetzung* der Herstellerstufe.

Jetzt öffnen beide Pfade einheitlich die **ersten zwei Stufen**. Das Handbuch beschreibt das tatsächliche Verhalten (vorher behauptete es drei Auto-Tabs).

## Kleinere Korrekturen
- `pen_widget._add`: fehlendes `session.rollback()` im Fehlerpfad ergänzt.
- Zwei überzählige Warn-Aufrufe in `_mark_cleaned`/`_unblock_pen` (Methoden ohne Bildimport) entfernt; ein Guard fixiert die Zahl auf exakt drei.

## Verifizierte Nicht-Findings (dokumentiert, NICHT gefixt)
- `safe_slug()` ist traversal-sicher (`"../../etc"` → `"etc"`).
- `is_inside()` löst vor dem Vergleich auf → kein Bypass.
- `reset_all_data()` prüft Containment korrekt (`data_root in resolved.parents`).
- Größenvergleich kann nicht durch Null teilen: `_collect_rows()` filtert Nulllängen.
- `_download_to()` ist nur über den http/https-Zweig erreichbar (kein `file://`).

## Absicherung
- **10 neue Tests** in `tests/test_media_import_non_fatal_0287.py`, davon **5 echte Verhaltenstests** gegen den Media-Service (übergroßer/leerer Download, Netzfehler, nicht-fataler fehlender Lokalpfad, korrekte Ablage im verwalteten Baum).
- **6 neue KILLCRITIC-Invarianten** → 76 × 20 = **1520 Checks, 0 Findings**.
- **Wirksamkeitsbeweis:** Die neuen Guards wurden gegen eine künstlich zurückgenommene Korrektur geprüft und schlagen dann nachweislich fehl. Lehre aus dieser Runde: Der 0.2.86-Reihenfolge-Guard war grün, obwohl das Feature wirkungslos war – er prüfte die *gebauten* URLs statt das *Öffnen*.

## Technik
- i18n: 2045 Keys × 3 (2 neue Schlüssel), Parität grün.
- Keine Änderungen an Engine, Regeln oder Datenbankschema.
