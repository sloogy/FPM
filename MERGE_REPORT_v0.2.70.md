# Merge Report – FountainPen Manager v0.2.70

**Datum:** 6. Juli 2026
**Build:** killcritic-dau-usability-merge
**Zusammengeführt:**
- **Strang A (Basis):** v0.2.69 KILLCRITIC (Dashboard-Aufräumung, Kontextmenüs,
  Ink-Reach & Kosten-Effizienz, Schreibproben, Enthusiast-Lab)
- **Strang B:** v0.2.52 DAU-Usability & UI-Konsistenz (einheitliche
  Hinzufügen-Buttons, Leerzustände für Wishlist/Ausgaben)

---

## Merge-Strategie

Die beiden Stränge waren **keine** gleichrangigen Feature-Branches derselben
Basis, sondern zwei unterschiedliche Stände:

- v0.2.69 baut auf v0.2.67 und ist funktional der **Obermenge**-Stand (enthält
  Schreibproben, Enthusiast-Lab, Ink-Reach usw.).
- v0.2.52 baut auf dem älteren v0.2.51 und trägt als **einzigen Mehrwert**
  gegenüber v0.2.69 die DAU-/UI-Konsistenz-Fixes.

Deshalb wurde v0.2.69 als Basis genommen und die Fixes aus v0.2.52 **hineinportiert**
(nicht per Datei-Überschreiben, sondern durch Anwenden derselben Änderungs-Absicht
auf die – teils neueren – Zieldateien). Vor jedem Port wurde geprüft, ob v0.2.69
den Punkt bereits enthält.

---

## Diff-Analyse: Was wurde portiert, was war schon da?

| Fix aus v0.2.52 | Zustand in v0.2.69 | Aktion |
|---|---|---|
| Einheitliche „+ X hinzufügen"-Buttons | Gleiche Inkonsistenz vorhanden | **Portiert** (pen, wishlist, expenses, rules) |
| Leerzustand Wishlist | Fehlte (blanke Tabelle) | **Portiert** (EmptyStateWidget + Stack) |
| Leerzustand Ausgaben | Fehlte (blanke Tabelle) | **Portiert** (EmptyStateWidget + Stack) |
| Speichern-Button-Abstand | Inkonsistent (ein Leerzeichen) | **Portiert** |
| Casing `leer`/`Leer` (Tinten) | **Bereits gelöst** (nutzt `t("...remaining_empty")`) | Übersprungen |
| `tests/test_db_smoke.py` (nur in 0.2.51) | Durch breitere Migrations-/Regressionstests abgelöst | Bewusst nicht portiert |

**Dateiabgleich:** Bis auf `test_db_smoke.py` enthält v0.2.69 alle Python-Dateien
von v0.2.51 – es ging beim Merge also kein Funktionsumfang verloren.

---

## Portierte Änderungen im Detail

### 1. Button-Konsistenz
Alle primären Anlege-Buttons folgen jetzt dem Muster **„+ <Objekt> hinzufügen"**
(DE/EN/FR). Vorher gemischt mit bloßem „+ Füller" / „+ Wunsch" / „+ Ausgabe".

### 2. Leerzustände für Wishlist & Ausgaben
Beide Listen zeigten bei leerer Sammlung eine blanke Tabelle. Jetzt erscheint der
gleiche `EmptyStateWidget`-Leerzustand wie bei Tinten/Federn/Papier (Icon,
erklärender Text, CTA-Button zum Anlegen), umgeschaltet über `QStackedWidget`.

**Merge-spezifische Korrektheit:** In v0.2.69 hat die Wishlist zusätzlich
Status-/Suchfilter. Der Leerzustand wird deshalb nur bei **wirklich leerer**
Sammlung gezeigt (`_has_any_wishes` vor den Filtern erfasst), nicht bei einem
leeren Filterergebnis – sonst würde ein „Noch keine Wünsche"-CTA fälschlich bei
10 vorhandenen, aber weggefilterten Einträgen erscheinen.

### 3. Neue Guard-Tests
`tests/test_ui_context_menus_static.py` wurde um drei statische Tests erweitert:
Leerzustand-Verdrahtung (Wishlist/Ausgaben), Button-Konsistenz-Muster und
Präsenz der neuen i18n-Keys in allen Sprachen.

---

## Validierung (Merge-Ergebnis)

```text
python -m compileall -q .            → OK (gesamter Baum)
Testsuite (headless Logik-Harness)   → 113 passed
  davon neu (Merge-Guards)           → 3 passed
tools/sync_version.py --check        → Alle Versionsdateien synchron: 0.2.70
tools/i18n_audit.py                  → OK (1903 Keys × 3 Sprachen)
tools/i18n_quality_audit.py          → OK (0 untranslated, 0 leakage)
tools/i18n_runtime_audit.py          → OK
tools/i18n_key_wiring_audit.py       → OK
tools/i18n_visible_text_audit.py     → OK
Key-Parität (eigenes Skript)         → de=en=fr=1903, 0 Waisen
```

Der einzige nicht ausgeführte Test ist der SQLAlchemy-abhängige
`test_logic_migration_hardening.py` (läuft in der echten Dev-/CI-Umgebung).

---

## Ehrliche Einschränkungen

- **Kein GUI-Smoke-Test:** PySide6 ist in der Sandbox nicht verfügbar. Die
  portierten Leerzustände folgen exakt dem bereits bewährten Muster von
  Tinten/Federn/Papier und kompilieren, wurden aber nicht in einem Desktop-Fenster
  geöffnet. Zu prüfen: Wishlist und Ausgaben je **leer** und **gefüllt** ansehen;
  bei der Wishlist zusätzlich prüfen, dass ein aktiver Filter mit 0 Treffern die
  leere Tabelle zeigt (nicht den „Noch keine Wünsche"-Zustand).
- **Kein echter Windows-Installer-Build** in dieser Umgebung.

---

## Urteil

**Freigabe empfohlen für v0.2.70 Source/Portable RC.**

Der Merge vereint die volle KILLCRITIC-Funktionalität (Dashboard-Aufräumung,
Kontextmenüs, Ink-Reach, Schreibproben, Enthusiast-Lab) mit den DAU-/UI-Konsistenz-
Verbesserungen in einem einzigen, konsistenten Stand.
