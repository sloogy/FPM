# v0.2.46 (merged) – Rotation/Rollen/Themen + Release-Härtung

Diese Version vereint zwei parallele Entwicklungslinien:
- **v0.2.45 (rotation-role-theme, erweitert)**: i18n-Vollabdeckung der Engine,
  editierbare Rollen UND Themen, Federgrössen-Scoring, Entfernung von totem Code,
  Behebung der Doppelbestrafung, Logging statt stiller Excepts, Test-Suite.
- **v0.2.46 (release-hardening)**: 6 gezielte Release-Fixes.

## Übernommen aus 0.2.46 (Release-Härtung)

1. `ui/paper_widget.py`: fehlender `QMenu`-Import ergänzt – Papier-Kontextmenü
   stürzt nicht mehr ab.
2. `ui/role_prefs_dialog.py`: Shading-Präferenz im Rollen-Editor sichtbar/editierbar.
   *(in der 0.2.45-Linie bereits behoben; hier bestätigt)*
3. `logic/role_config.py`: bevorzugte Füllsysteme wirken jetzt im Scoring
   (`_score_ink_for_config`), übersetzt über `t()` und für Rollen **und** Themen.
4. `logic/rotation_engine.py`: Clean+Refill (`get_refill_recommendations_for_pen`)
   lädt benutzerdefinierte Rollen- **und** Themen-Konfigurationen.
5. `logic/rotation_engine.py`: Pflicht-Füller/feste Paarungen werden über ALLE
   Kandidaten erkannt (nicht nur den Top-Score); feste Paarung bevorzugt wirklich
   die feste Tinte.
6. `logic/rotation_engine.py`: generischer `writer`-Default blockiert die
   Auto-Rollenerkennung nicht mehr – Tags/Pflichtstatus/Feder-Fallback dürfen ihn
   übersteuern.

## Beibehalten aus der 0.2.45-Linie

- Vollständige i18n der Rotations-Hinweise, Status- und Fill/Drain-Meldungen
  (~80 zusätzliche Keys × DE/EN/FR).
- Editierbare Rollen **und** Themen über gemeinsamen Scoring-Kern
  `_score_ink_for_config`; Dialog mit „Rollen | Themen"-Tabs.
- Federgrössen-Kategorien + Scoring; keine Doppelbestrafung von Nässe/Pigment
  (Nib übernimmt Physik, Rolle den Einsatzzweck).
- DB-Importe in `logic/role_config.py` sind lazy → reines Scoring ohne
  SQLAlchemy nutz- und testbar.
- Logging statt stiller `except`-Blöcke.
- `tests/` mit 36 Tests (pytest-kompatibel).

## Validierung

- `python -m compileall -q .` → OK
- `python dev_check.py` → OK
- `python tools/i18n_audit.py` → 1164 Keys × 3 Sprachen
- `python tools/i18n_quality_audit.py` → 0 untranslated / 0 leakage / 0 ternary
- `python tools/i18n_key_wiring_audit.py` → 0 hartkodierte Literale
- `python tools/i18n_runtime_audit.py` → OK
- `pytest tests/ -v` → 36 passed

Kein Datenbankschema geändert.
