# Release Report – FountainPen Manager v0.2.68 KILLCRITIC

**Datum:** 6. Juli 2026
**Basis:** v0.2.67 KILLCRITIC Reference Images / Filldata
**Ziel:** Tiefe Releasefähigkeitsanalyse, Fix offener Punkte, sinnvolle
Erweiterung für Enthusiasten **und** Hobby-Sammler.

---

## Executive Summary

v0.2.68 ist als Source-/Portable-Release-Kandidat freigabefähig.

Die kritische Prüfung von v0.2.67 ergab: Die Basis ist tatsächlich so stabil
wie der letzte Report behauptet. Tests, i18n-Parität (inkl. dynamischer
Laufzeit-Keys), Rotation-/Safety-Logik und Referenzdaten-Workflow sind sauber.
Es wurden **keine erfundenen Pseudo-Findings** produziert.

Die eine reale Lücke war funktional, nicht defekt: Die Füll-Historie jeder
Tinte lag vor, wurde aber nirgends zu einer Reichweiten-, Prognose- oder
Kostensicht verdichtet. Genau das schließt diese Version – für Enthusiasten
(„wann ist die Flasche leer?") und für Sammler („wie wirtschaftlich ist sie?").

Zusätzlich wurde ein toter, veralteter i18n-Versionswert bereinigt.

---

## 100er KILLCRITIC-Loop – 10 Themen × 10 Prüfpunkte

| Thema | Prüfschwerpunkt | Ergebnis |
|---|---|---|
| 1. Start/Import-Struktur | Imports, `compileall` gesamter Baum, Modultrennung | OK |
| 2. Datenbank/Migration | additive Migration, SCHEMA_VERSION-Marker, keine Destruktivmigration | OK, Schema 0.2.68 |
| 3. Rotation/Scoring | aktive-Tinte-Dedup, fixe Paarung, Verbrauch via `apply_ink_consumption` | verifiziert, unverändert korrekt |
| 4. Tintenlogik | Restmenge, Clamp, Nachkauf, **neue Reichweite/Kosten** | erweitert |
| 5. Sammlerlogik/Wert | Kosten/ml, Kosten/Füllung, verbrauchter/Rest-Wert, Aggregat | neu |
| 6. Enthusiasten-Usability | Reichweite, Ø-Füllung, Leerdatum-Prognose im Tinten-Detail | neu |
| 7. Mehrsprachigkeit | DE/EN/FR Parität, dynamische Keys, neue Reach-Keys | OK, 1892 Keys × 3 |
| 8. Tests/Regression | 103 Logik-Tests grün (+11 neu), Version-Pins nachgezogen | OK |
| 9. Versionierung/Installer | `sync_version --check` grün, alle Templates synchron | OK, 0.2.68 |
| 10. Release-Hygiene | Pycache/Cache entfernt, Changelog/Report ergänzt | bereinigt |

---

## Unabhängig durchgeführte Prüfungen (nicht nur Reports geglaubt)

1. **Key-Parität hart nachgerechnet:** de=en=fr=1892, 0 Waisen in jede Richtung.
2. **Dynamische Laufzeit-Keys aufgelöst:** `enthusiast_lab.status.ink.*`,
   `enthusiast_lab.recommendations.ink.*` und neu `enthusiast_lab.reach.status.*`
   existieren für **alle** konkreten Statuswerte in allen drei Sprachen –
   genau die Stelle, an der statische Audits einen Roh-Key übersehen würden.
3. **Rotation-Engine gelesen:** aktive-Tinte-Skip (`get_suggestions`) und
   Duplikat-Malus (`_score_pen_ink`) sind konsistent; `fill_pen` bucht Verbrauch
   zentral und verhindert negative Restmengen.
4. **Stale-Version-Falle gefunden:** i18n-Key `app.version` stand auf `v0.2.62`,
   wird aber nirgends per `t()` aufgerufen. Kein Nutzer-Bug, aber eine latente
   Falle → auf aktuellen Stand synchronisiert.

---

## Neue Funktion im Detail

`logic/ink_reach_service.py` (reine Logik, DB-frei, voll getestet):

- `ink_reach_row(ink)` / `ink_reach_rows(inks)` – pro Tinte:
  erfasste Füllungen, Ø-Füllmenge, geschätzte Restfüllungen, Verbrauch/Tag,
  Leerdatum-Prognose, Kosten/ml, Kosten/Füllung, verbrauchter/Rest-Wert, Status.
- `collection_ink_value_summary(inks)` – Sammlungssicht mit wirtschaftlichster/
  teuerster Tinte und Währungs-Sicherung (`mixed` statt Falschsumme).

Sicherheitsnetze: nur real erfasste Füllungen (Volumen > 0), Rate erst ab
≥ 14 Tagen Beobachtung, keine geratenen Werte, keine Mutation.

Angebunden im Tinten-Detail (`ui/ink_widget.py`) über das bestehende
`row()`-Muster, statusabhängig eingefärbt, nur bei belegten Daten sichtbar.

---

## Validierung

```text
python -m compileall -q .            → OK (gesamter Baum)
Testsuite (headless Logik-Harness)   → 103 passed
  davon neu: tests/test_ink_reach_service.py → 11 passed
tools/sync_version.py --check        → Alle Versionsdateien synchron: 0.2.68
tools/i18n_audit.py                  → OK (1892 Keys × 3 Sprachen)
tools/i18n_quality_audit.py          → OK (0 untranslated, 0 leakage)
tools/i18n_runtime_audit.py          → OK
tools/i18n_key_wiring_audit.py       → OK
tools/i18n_visible_text_audit.py     → OK
Key-Parität (eigenes Skript)         → de=en=fr=1892, 0 Waisen
```

---

## Ehrliche Einschränkungen

- **Kein GUI-Smoke-Test:** PySide6 ist in der Prüf-Sandbox nicht verfügbar. Die
  neue Anzeige im Tinten-Detail folgt dem bestehenden, bewährten `row()`-Muster
  und dem offenen Session-Kontext (direkt darunter wird `ink.ink_loads` bereits
  genutzt), wurde aber **nicht** in einem echten Desktop-Fenster geöffnet.
- **Migrationstest:** `tests/test_logic_migration_hardening.py` (4 Tests) braucht
  SQLAlchemy und läuft in der echten Dev-/CI-Umgebung, nicht in dieser Sandbox.
  Er ist versionsagnostisch (prüft nur gespeicherte == `SCHEMA_VERSION`).
- **Kein echter Windows-Installer-Build** in dieser Umgebung ausgeführt.

---

## Releaseurteil

**Freigabe empfohlen für v0.2.68 Source/Portable RC.**

Für ein finales öffentliches Windows-Release bleiben die bekannten manuellen
Schritte: echter Windows-Build, Installer-Test und GUI-Smoke-Test – insbesondere
ein Blick ins Tinten-Detail mit einer Tinte, die Füll-Historie **und** Preis-/
Größenangaben besitzt, um die neuen Kennzahlen einmal live zu sehen.
