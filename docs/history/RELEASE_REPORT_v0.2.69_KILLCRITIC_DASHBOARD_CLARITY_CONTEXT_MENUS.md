# Release Report – FountainPen Manager v0.2.69 KILLCRITIC

**Datum:** 6. Juli 2026
**Basis:** v0.2.68 KILLCRITIC Ink Reach & Cost Efficiency
**Ziel:** Kritische Releaseanalyse, Dashboard/UI übersichtlicher, fehlende
Rechtsklick-Optionen ergänzen.

---

## Executive Summary

v0.2.69 ist als Source-/Portable-Release-Kandidat freigabefähig.

Diese Runde adressiert die zwei ausdrücklich genannten Punkte: Das Dashboard war
unübersichtlich, weil **alle** Abschnitte immer sichtbar waren – auch leere. Und
mehreren Listen fehlten Rechtsklick-Menüs. Beides ist behoben; die Änderungen
folgen strikt den bereits im Projekt etablierten Mustern.

Ehrliche Einordnung: Es sind UI-Änderungen, und PySide6 lässt sich in dieser
Sandbox nicht ausführen. Die Verdrahtung ist deshalb bewusst konservativ,
kompiliert sauber, ist statisch getestet – ein manueller GUI-Smoke-Test bleibt
der letzte Schritt vor dem finalen Release.

---

## 100er KILLCRITIC-Loop – 10 Themen × 10 Prüfpunkte

| Thema | Prüfschwerpunkt | Ergebnis |
|---|---|---|
| 1. Start/Import-Struktur | `compileall` gesamter Baum, neue Imports | OK |
| 2. Datenbank/Migration | keine strukturelle Migration, SCHEMA_VERSION-Marker | OK, 0.2.69 |
| 3. Dashboard-Übersicht | leere Abschnitte ausblenden, „Alles im grünen Bereich" | umgesetzt |
| 4. Rechtsklick Dashboard | Sprung-Navigation, Details kopieren, aktualisieren | umgesetzt |
| 5. Rechtsklick Schreibproben | Neu/Bearbeiten/Vergleichen/Löschen | umgesetzt |
| 6. Rechtsklick Enthusiast-Lab | zur Tinte springen, Restmenge, kopieren | umgesetzt |
| 7. Signal-/Navigations-Kopplung | `navigate_to` Auto-Wiring wie `tour_requested` | verifiziert |
| 8. i18n DE/EN/FR | Parität, neue Kontext-Keys, dynamische Keys | OK, 1897 × 3 |
| 9. Tests/Regression | +7 statische UI-Guards, Version-Pins nachgezogen | 110 grün |
| 10. Versionierung/Release-Hygiene | sync grün, Pycache bereinigt, Changelog/Report | OK |

---

## Kritische Punkte, die ich aktiv geprüft habe

1. **None-is-None-Falle bei Kontextmenüs.** Optionale Menüaktionen sind bei
   manchen Tabellen `None` (z. B. „Zur Tinte springen" fehlt in der
   Service-Tabelle). Ohne Schutz würde das Verwerfen des Menüs (`exec()` gibt
   `None` zurück) den `None`-Zweig treffen und fälschlich navigieren. Gelöst
   durch expliziten `if chosen is None: return`-Guard direkt nach `exec()`;
   zusätzlich sind reale QActions nie `None`. Der Guard-Test prüft genau das.
2. **Variablen-Scope in `refresh()`.** Die neue Sichtbarkeitslogik greift auf
   `timer_rows`, `service_rows`, `health_rows`, `loads`, `warnings` zu – alle
   werden vor dem Sichtbarkeits-Block unbedingt initialisiert.
3. **Signal-Kopplung ohne Fragilität.** `navigate_to` wird über den bereits
   vorhandenen `getattr(widget, ...)`-Hook im Hauptfenster verbunden – kein
   neuer Zwang, keine Importzyklen, dasselbe Muster wie `tour_requested` und
   das `navigate_to` des Onboarding-Wizards.
4. **i18n-Disziplin.** Alle neuen sichtbaren Texte laufen über `t()`-Keys mit
   voller DE/EN/FR-Parität; Schreibproben-/Lab-Menüs verwenden bestehende Keys
   wieder. Alle fünf i18n-Audits bleiben grün.

---

## Validierung

```text
python -m compileall -q .            → OK (gesamter Baum)
Testsuite (headless Logik-Harness)   → 110 passed
  davon neu: tests/test_ui_context_menus_static.py → 7 passed
tools/sync_version.py --check        → Alle Versionsdateien synchron: 0.2.69
tools/i18n_audit.py                  → OK (1897 Keys × 3 Sprachen)
tools/i18n_quality_audit.py          → OK (0 untranslated, 0 leakage)
tools/i18n_runtime_audit.py          → OK
tools/i18n_key_wiring_audit.py       → OK
tools/i18n_visible_text_audit.py     → OK
Key-Parität (eigenes Skript)         → de=en=fr=1897, 0 Waisen
```

---

## Ehrliche Einschränkungen

- **Kein GUI-Smoke-Test:** PySide6 ist in der Prüf-Sandbox nicht verfügbar. Die
  neuen Menüs und die Dashboard-Sichtbarkeit folgen exakt bestehenden,
  bewährten Mustern und kompilieren, wurden aber **nicht** in einem echten
  Desktop-Fenster geöffnet. Zu prüfen ist insbesondere:
  Rechtsklick in jeder der genannten Tabellen, „Zum Füller/Tinte springen"
  (Seitenwechsel), „Details kopieren" (Zwischenablage) und das Ein-/Ausblenden
  der Dashboard-Abschnitte bei leerer vs. gefüllter Sammlung.
- **Migrationstest** (`test_logic_migration_hardening.py`, 4 Tests) braucht
  SQLAlchemy und läuft nur in der echten Dev-/CI-Umgebung.
- **Kein echter Windows-Installer-Build** in dieser Umgebung ausgeführt.

---

## Releaseurteil

**Freigabe empfohlen für v0.2.69 Source/Portable RC.**

Für ein finales öffentliches Windows-Release bleiben die bekannten manuellen
Schritte: echter Windows-Build, Installer-Test und ein GUI-Smoke-Test mit
besonderem Blick auf die neuen Rechtsklick-Menüs und das aufgeräumte Dashboard.
