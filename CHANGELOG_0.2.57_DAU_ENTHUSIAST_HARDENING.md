# v0.2.57 – DAU-/Enthusiasten-Hardening

Basis: v0.2.56 DAU-Usability-Merge.

## Releasefähigkeit

- `app_info.py` auf `0.2.57` / Build `dau-enthusiast-hardening` aktualisiert.
- README von v0.2.55 auf den tatsächlichen Release-Stand v0.2.57 gehoben.
- GitHub Release-Check ergänzt `tools/i18n_visible_text_audit.py`, damit sichtbare UI-Texte in DE/EN/FR mitgeprüft werden.
- Neue Regressionstests für Sammlungs-Advisor und BudgetManager-Export ergänzt.

## DAU-Freundlichkeit

- Neues Dashboard-Modul **Sammlungs-Advisor**:
  - erkennt leere, rotationsbereite Füller,
  - priorisiert überfällige Befüllungen nach Safety-Limit,
  - zeigt gesperrte/Service-Füller,
  - meldet niedrige oder leere Tintenstände,
  - warnt bei fast vollem Papier/Notizbuch,
  - erinnert an bald ablaufende Garantie,
  - weist auf fehlende Fotos oder fehlende Wert-/Kaufpreisdaten hin.
- Hinweise ändern nichts automatisch. Der Nutzer sieht nur klare nächste Schritte.

## Enthusiasten-/Sammlerfunktionen

- Neuer reiner Service `logic/collection_health_service.py` als Grundlage für Inventar-Health, Wartungsplanung und Sammler-Checkliste.
- Aktive Shimmer-/Pigment-/schwer reinigbare Tinten werden als Reinigungsrisiko hervorgehoben.
- Wert-/Inventarvollständigkeit wird sichtbar, ohne Anfänger mit Tabellenpflege zu überfordern.

## BudgetManager-Schnittstelle

- Neuer reiner Service `logic/budget_export_service.py`.
- Einstellungen → Import / Export enthält jetzt **BudgetManager-JSONL exportieren**.
- Exportformat:
  - Manifest-Zeile `budgetmanager.import.manifest.v1`,
  - eine Zeile pro Ausgabe `budgetmanager.import.v1`,
  - stabile `external_id` für spätere Upserts,
  - Kategorien wie `Hobby/Füller`, `Hobby/Tinte`, `Hobby/Papier`, `Hobby/Service`, `Hobby/Versand/Zoll`.
- Bewusst Einweg-Datei statt direktem DB-Zugriff.

## Validierung

- `python -m compileall -q .` ✅
- `python -m pytest -q -ra` ✅ – 53/53 Tests
- `python tools/i18n_audit.py` ✅ – 1581 Keys × 3 Sprachen
- `python tools/i18n_quality_audit.py` ✅
- `python tools/i18n_key_wiring_audit.py` ✅
- `python tools/i18n_runtime_audit.py` ✅
- `python tools/i18n_visible_text_audit.py` ✅

## Nicht automatisch geprüft

- GUI-Start mit echter PySide6-Installation in dieser Sandbox nicht möglich, weil PySide6 hier nicht installiert ist.
- Sichtprüfung der neuen Dashboard-Tabelle und des Datei-Dialogs sollte lokal erfolgen.
- Paketbau als ausführbare Anwendung wurde statisch vorbereitet, aber nicht als EXE/AppImage gebaut.
