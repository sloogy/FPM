# Fixes 0.2.39 – Logik/UI-Konsistenz

Diese Version behebt die in der Deep-Analyse gefundenen Logik- und UI-Probleme nach v0.2.38.

## Kritisch
- Papier-Kontext-Score nutzt jetzt `Paper.sheen_suitable` statt des falschen Feldnamens `sheen_suitability`.
- Der Score-Erklärdialog liest das Vorschlags-Dict jetzt aus der Score-Spalte und ist dadurch wieder erreichbar.

## Hoch
- Dashboard-Safety-Timer verwendet jetzt zentral `RuleEngine.max_days_for(...)` statt einer eigenen Fallback-Logik.
- Manuelles Einfüllen läuft über `RotationEngine.fill_pen(...)`; harte Regeln, Override-Grund, Verbrauchsbuchung und OverrideLog gelten nun auch dort.
- `clean_and_refill(...)` und `apply_suggestion(...)` nutzen dieselbe zentrale Befüllmethode.
- Systemregeln werden beim Start nicht mehr überschrieben; Systemregeln können editiert, aber nicht mehr physisch gelöscht werden. Löschen deaktiviert sie.
- `expenses_changed` wird jetzt vom Ausgaben-Widget emittiert und von Dashboard/Ausgaben-Widget verarbeitet.

## Mittel
- Doppelte Score-Zählung von Beliebtheit, Pflicht-Füller und fester Paarung entfernt: Diese Faktoren bleiben in `RuleEngine.score(...)` und werden in `RotationEngine.get_suggestions(...)` nicht nochmals addiert.
- Harte Regeln mit `warn_level=info` werden im UI als Override-pflichtig erkannt.
- Tour-Overlay wird bei Resize/Show neu gerendert; Spotlight, Bubble und Abbruch-Button folgen dem Fenster.

## Niedrig/Politur
- Dashboard-Karte `WARNUNGEN` heißt jetzt `SAFETY-TIMER`, weil nur überfällige Timer gezählt werden.
- `ARCHIVIERT` zählt nun Füller + Tinten und zeigt Details im Tooltip.
- Factory Reset löscht nun Bilddateien unter `~/.fpm_data/images/...`, sofern sie innerhalb des App-Datenordners liegen.
- `InkLoad.days_loaded` dokumentiert explizit, dass volle 24h-Tage gezählt werden.
