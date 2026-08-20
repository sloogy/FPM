# Tiefe kritische Release-Analyse – FountainPen Manager v0.2.87

**Auftrag:** Kritische Prüfung auf Releasefähigkeit. Nicht „laufen die Audits grün?", sondern: *Was übersehen die Audits?*

**Methodik:** Bewusst dort gesucht, wo die bestehende Prüfmaschinerie blind ist – im Code, der aus dem 0.2.84-Parallelzweig übernommen wurde, ohne dass ich ihn je zeilenweise gelesen hatte. Dazu gezielte Suche nach den Fehlerklassen, die statische Audits und i18n-Prüfungen strukturell nicht sehen können: Transaktionsgrenzen, Exception-Fluss, Datenverlust, Doku-Verhalten-Mismatch.

**Ergebnis: 2 echte Fehler (1 kritisch), 3 kleinere Mängel, 4 verifizierte Nicht-Findings.**

---

## Teil 1 – Kritische Findings

### 🔴 FINDING 1 (kritisch, Datenverlust): Fehlgeschlagener Bild-Import zerstört den Datensatz

**Betroffen:** `ui/pen_widget.py` (`_add`, `_edit_pen_by_id`, `_copy_pen`), `ui/writing_samples_widget.py` (`_add`, `_edit`)

**Der Fehler:**
```python
session.add(pen)
session.flush()
self._store_pen_image_if_needed(pen)   # <- kann werfen: Download, Timeout, "zu groß"
session.commit()                       # <- wird nie erreicht
...
except Exception as e:
    QMessageBox.critical(...)          # kein Commit / Rollback -> Füller weg
```

`import_pen_image()` lädt bei einer URL synchron herunter (15 s Timeout) und wirft bei jedem Problem:
- `ValueError("Bilddatei ist zu groß.")` bei > 15 MB,
- `ValueError("Leere Bilddatei erhalten.")`,
- `OSError` bei jedem Netzwerkfehler,
- `PermissionError`/`OSError` beim lokalen Kopieren.

**Wirkung:** Der Nutzer trägt einen Füller vollständig ein – Marke, Modell, Kaufpreis, Maße, Feder, Tags – fügt ein Bild aus dem Netz hinzu, klickt OK. Das Bild ist 16 MB groß. Ergebnis: Fehlerdialog, **alle Eingaben verloren**. Der Datensatz war fachlich einwandfrei; ein kosmetisches Beiwerk hat ihn getötet. In `writing_samples` sogar mit explizitem `session.rollback()`.

**Warum kein Audit das fand:** compileall, i18n-Audits und die statischen KILLCRITIC-Invarianten prüfen Struktur und Texte, nicht Transaktionssemantik. Die Unit-Tests des Media-Service testen den Service isoliert – der Service *soll* ja werfen. Niemand prüfte, was der Aufrufer damit tut.

**Fix:** Der Import ist jetzt nicht-fatal. Fehler werden abgefangen, der ursprüngliche Pfad/die URL bleibt am Datensatz (der Media-Service tut das ohnehin für nicht existierende lokale Pfade), der Commit läuft durch, und **nach** erfolgreichem Commit erscheint eine Warnung mit dem konkreten Grund. Zusätzlich fehlte in `pen_widget._add` ein `session.rollback()` im Fehlerpfad – ergänzt.

**Grundsatz dahinter:** *Ein optionales Beiwerk darf niemals eine Pflichtoperation kippen.*

---

### 🟠 FINDING 2 (mittel, Doku-Verhalten-Mismatch): Die „Kaskade" öffnete nur eine Stufe

**Betroffen:** `ui/pen_widget.py`, der Dialog „Kein sicherer Treffer" (genau der aus dem gemeldeten Screenshot)

**Der Fehler:**
```python
opened = bool(webbrowser.open(result.search_urls[0]))        # nur [0]
opened_image = bool(webbrowser.open(result.image_search_urls[0]))
```
während `_open_pen_image_search()` an anderer Stelle `urls[:2]` öffnete – zwei Pfade, zwei Verhalten.

**Wirkung:** Ich hatte in v0.2.85/0.2.86 eine dreistufige Kaskade gebaut und im Handbuch geschrieben: *„Beide Recherche-Buttons öffnen eine dreistufige Kaskade (jede Stufe ein Tab)"*. Das war **falsch**. Real bekam der Nutzer bei den Maßen genau einen Tab. Die fachlich wichtige zweite Stufe – bei Maßen die Herstellerseite, bei Bildern der KI-Prompt – wurde korrekt berechnet und dann verworfen. Meine Reihenfolge-Umstellung in 0.2.86 („KI zuerst") war dadurch faktisch eine *Ersetzung* statt einer Priorisierung: Die Herstellerstufe war für die Maße unerreichbar.

**Besonders unangenehm:** Der KILLCRITIC-Reihenfolge-Guard aus 0.2.86 war grün. Er prüfte die *Reihenfolge der gebauten URLs* – nicht, ob sie jemals geöffnet werden. Ein Guard, der die Absicht misst statt die Wirkung.

**Fix:** Beide Pfade öffnen einheitlich die ersten **zwei** Stufen (Maße: KI + Hersteller; Bilder: Hersteller + KI). Die dritte Stufe bleibt Rückfallebene ohne Auto-Tab. Das Handbuch beschreibt jetzt das tatsächliche Verhalten.

---

## Teil 2 – Kleinere Mängel (behoben)

| # | Mangel | Fix |
|---|---|---|
| 3 | `pen_widget._add` hatte kein `session.rollback()` im Fehlerpfad (Session wurde mit offener Transaktion geschlossen) | Ergänzt |
| 4 | Meine Warn-Einfügung traf per Textmuster auch `_mark_cleaned` und `_unblock_pen` – Methoden ohne Bildimport | Entfernt; Guard fixiert die Zahl auf exakt 3 |
| 5 | Handbuch behauptete drei Auto-Tabs | Auf tatsächliches Verhalten korrigiert |

---

## Teil 3 – Verifizierte Nicht-Findings

Ausdrücklich dokumentiert, damit sie nicht in einer späteren Runde „prophylaktisch" gefixt werden. Ein Phantom-Fix ist schlimmer als kein Fix, weil er Vertrauen in einen Bericht zerstört.

| Verdacht | Prüfung | Ergebnis |
|---|---|---|
| **Pfad-Traversal** über Marke/Modell in Medienordnern | `safe_slug("../../etc")` → `"etc"`; `safe_slug("...")` → `"item"`; Regex lässt nur `[A-Za-z0-9._-]` durch, strippt führende Punkte | **Sicher** |
| **Containment-Bypass** in `is_inside()` | `is_inside("/tmp/root/../evil", "/tmp/root")` → `False` (resolve vor relative_to) | **Sicher** |
| **`reset_all_data` löscht Dateien außerhalb des Datenverzeichnisses** | Guard `data_root in resolved.parents` nach `resolve()` – korrektes Containment | **Sicher** |
| **Division durch Null** im Größenvergleich (`scale = usable / max_len`) | `_collect_rows()` filtert Füller mit `max(closed, uncapped, posted) <= 0` heraus; jede verbleibende Zeile liefert `> 0`. Leere Auswahl → `max_len = 1` | **Kann nicht auftreten** |
| **`file://`-Lesen über `_download_to`** | Funktion ist ausschließlich über den `raw.startswith(("http://","https://"))`-Zweig erreichbar | **Nicht ausnutzbar** (siehe Restrisiko unten) |

---

## Teil 4 – Bekannte Restrisiken (nicht behoben, bewusst)

1. **Blockierender Netzaufruf im GUI-Thread.** `_download_to` hat 15 s Timeout und läuft synchron. Bei einem hängenden Server friert die Oberfläche bis zu 15 s ein. Nach dem Fix ist das *nur noch* ein Komfortproblem (keine Daten mehr in Gefahr). Sauber wäre ein `QThread`/Worker – ein eigener, testbarer Umbau, kein Hotfix-Material.
2. **`_download_to` prüft den Content-Type nicht.** Eine HTML-Fehlerseite unter `.jpg` würde als Bild gespeichert. Kosmetisch; Größenlimit und Suffix-Whitelist greifen. Eine Magic-Byte-Prüfung wäre die saubere Lösung.
3. **`urllib` folgt Redirects** (http→https→ftp erlaubt). Kein realistischer Angriffsvektor für eine lokale Sammler-App mit vom Nutzer eingegebener URL, aber erwähnenswert.
4. **`reset_all_data` lässt leere Medien-Unterordner zurück** (`media/<pen>/images/`). Dateien werden korrekt gelöscht, nur `rmdir` scheitert am nicht-leeren Wurzelverzeichnis. Rein kosmetisch.
5. **Kein GUI-Smoke-Test** (PySide6 fehlt in der Sandbox). Alle UI-Aussagen dieser Analyse beruhen auf Quelltext-Lektüre, nicht auf Beobachtung.

---

## Teil 5 – Selbstkritik an der Prüfmaschinerie

Zwei Lehren, die über diese Version hinausgehen:

**a) Ein grüner Guard beweist nichts, solange er nicht auch rot werden kann.** Der 0.2.86-Reihenfolge-Guard war grün, während das Feature faktisch nicht existierte, weil er die *gebaute* URL-Liste prüfte statt das *Öffnen*. Alle sechs neuen Invarianten dieser Runde wurden deshalb gegen eine künstlich zurückgenommene Korrektur getestet und schlagen dann nachweislich fehl (`media_import_non_fatal_pen: False`, `lookup_opens_two_stages: False`).

**b) Übernommener Fremdcode braucht dieselbe Prüftiefe wie eigener.** Beide Findings stecken in Code, den ich aus dem 0.2.84-Zweig übernommen habe. Im damaligen Merge-Report stand, die Features seien „vollständig und sinnvoll" – das war eine Aussage über die Feature-*Liste*, nicht über die Implementierung. Genau dieselbe Fehlerklasse wie die `site:`-Fehleinschätzung im 0.2.80-Merge.

---

## Teil 6 – Validierung

```text
python3 -m compileall -q .                    OK
python3 tools/sync_version.py --check         Alle Versionsdateien synchron: 0.2.87
python3 tools/i18n_audit.py                   OK (2045 Keys × 3 Sprachen)
python3 tools/i18n_quality_audit.py           OK
python3 tools/i18n_runtime_audit.py           OK
python3 tools/i18n_key_wiring_audit.py        OK
python3 tools/i18n_visible_text_audit.py      OK
python3 tools/killcritic_1000_loop_audit.py   OK (76 × 20 = 1520 Checks, 0 Findings)
Tests (headless Shim)                         200 passed, 1 failed*
```
\* `test_logic_migration_hardening.py` benötigt echtes SQLAlchemy (netzlose Sandbox). Kein Code-Defekt.

**Neue Tests (10):** fünf echte Verhaltenstests gegen den Media-Service (übergroßer Download, leerer Download, Netzfehler, fehlende lokale Datei bleibt nicht-fatal, lokale Kopie landet im verwalteten Baum), Slug-/Containment-Sicherheit, sowie Aufrufer-Guards (Abfangen, Rohpfad-Erhalt, Warnung erst nach Commit, exakt drei Warnstellen, Rollback in `_add`, i18n-Parität mit `{error}`-Platzhalter).

---

## Release-Urteil

**Freigabe empfohlen für v0.2.87 Source/Portable RC.**

Das kritische Finding 1 war ein echter Release-Blocker: stiller Datenverlust bei einer alltäglichen Handlung (Bild per URL hinzufügen). Es ist behoben und durch diskriminierende Guards abgesichert. Finding 2 machte ein dokumentiertes Feature faktisch wirkungslos; ebenfalls behoben.

**Vor dem öffentlichen Release weiterhin nötig:** manueller GUI-Smoke-Test auf Windows, Installer-Build, Praxis-Check der Recherche-Tabs. Diese Punkte kann die Sandbox nicht abdecken – das ist eine Grenze der Umgebung, keine Formalie.

**Konkrete Verifikation für Christian:**
1. Füller anlegen, als Bild-URL eine sehr große Datei (> 15 MB) oder eine tote URL eintragen → **Füller muss gespeichert werden**, Warnhinweis erscheint, Bildpfad bleibt als Text erhalten.
2. „Maße suchen" → **zwei** Tabs: Google-KI-Prompt, dann `site:hersteller.com <Modell>`.
3. „Bilder suchen" → **zwei** Tabs: Herstellerbilder, dann KI-Prompt.
