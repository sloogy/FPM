# v0.2.28 Ruleset Hardening

Umgesetzt:

- Regelgruppen einzeln schaltbar in Regeln & Reinigungszeiten.
- Neue Gruppen: `ink_fill` für Tinten-Füllregeln und `consumption` für automatische Restmengen-/Verbrauchsbuchung.
- Full Auto Mode respektiert globale Regel- und Gruppenschalter.
- Bestehende Systemregeln werden beim Start auf den aktuellen Regelkatalog gehärtet, damit neue Gruppen auch in alten Datenbanken greifen.
- Vac/Eyedropper + Shimmer/Pigment liegen jetzt in `ink_fill` statt pauschal `safety`.
- Automatische Reduktion von `remaining_ml` und automatisches `is_empty` setzen sind über die Gruppe `consumption` abschaltbar.
- Direkte Füllung, Leeren+Befüllen und Rotationsvorschlag-Übernahme respektieren den Verbrauchsschalter.

Hinweis: Wenn `consumption` deaktiviert ist, werden InkLoads weiter protokolliert, aber Tinten-Restmengen nicht automatisch reduziert.
