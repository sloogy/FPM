# Fixes 0.2.40 – Deep Runtime Hardening

Diese Version geht über den Logik/UI-Hotfix 0.2.39 hinaus und härtet vor allem Migrationen, Runtime-Konsistenz und kleinere UI-Sackgassen.

## Kritisch

- Fehlende SQLite-Migrationen ergänzt:
  - `nibs.feedback_level`
  - `papers.image_path`
  - `nib_formats.compatible_with`
  - `nib_formats.notes`
  - alle neueren `pen_nib_setups`-Workflow-Felder
- Dadurch starten ältere Datenbanken nicht mehr mit `OperationalError: no such column ...`, wenn sie vor dem Nib-/Papier-Workflow erzeugt wurden.
- `schema_version` wird jetzt auf `0.2.40` gesetzt.

## Hoch

- `RuleEngine.max_days_for(...)` erkennt den Tag `Grail` jetzt case-insensitive. Vorher griff die Grail-Reinigungsfrist nur bei exakt kleinem `grail`.
- Aktuelle Rotation zeigt jetzt auch bereits befüllte Problem-/Service-/gesperrte Füller. Solche Füller bleiben weiterhin für neue Befüllvorschläge blockiert, verschwinden aber nicht mehr aus der Safety-/Reinigungssicht.
- Entsperren eines Füllers löscht jetzt auch Service-Daten (`service_start_date`, `service_days`, `service_cost`, `service_currency`, `service_notes`).
- Globales `reset_pen_status()` löscht ebenfalls `service_currency`.

## Mittel

- Papierwechsel im Rotations-Tab berechnet sichtbare Vorschläge sofort neu, damit Papier-Score und angezeigte Vorschläge nicht veralten.
- Doppelklick auf die Score-Spalte übernimmt nicht mehr versehentlich den Vorschlag, sondern öffnet/zeigt nur die Erklärung.
- `EventBus.emit_all()` feuert jetzt auch wirklich `all_changed`.
- Factory Reset löscht jetzt auch benutzerdefinierte `NibFormat`-Einträge.
- Regeln-Dialog erlaubt jetzt optionales `score_delta`; leer bedeutet weiterhin Fallback nach Warnstufe.

## Politur

- Score-Tooltip im Rotations-Tab an die tatsächlichen Werte angepasst.
- Doppelte `_refresh_cleaning()`-Ausführung beim „keine Vorschläge“-Fall entfernt.
- Aktuelle Belegung zeigt Status-/Sperrhinweise an, wenn ein befüllter Füller nicht verfügbar ist.

## Prüfung

- `python -m compileall -q .` erfolgreich.
- Headless Fresh-DB-Smoke-Test erfolgreich: DB-Init, Default-Inks, `schema_version=0.2.40`.
- Headless UI-Smoke-Test erfolgreich: alle Hauptwidgets instanziierbar.
- Migrationstest erfolgreich: simulierte Alt-DB ohne mehrere neue Spalten wird migriert und ORM-Zugriff funktioniert.
- Grail-Reinigungsfrist-Test erfolgreich: `tags='Grail'` ergibt 21 Tage.
