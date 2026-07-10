# Release Report – FPM v0.2.61

## Ziel

v0.2.60 bleibt Architektur-Basis. Die guten Kontext-Ideen aus der alternativen v0.2.59-Enthusiastenlinie wurden integriert, ohne die sauberere v0.2.60-Datenstruktur zu verwässern.

## Änderungen

- Kontextbuttons im Füller-Detail:
  - neue Schreibprobe mit vorausgewähltem Füller
  - Vergleich der letzten 2–4 Schreibproben dieses Füllers
  - Federhistorie aus `pen_nib_setups`
  - Feder-/Setup bearbeiten über bestehenden Füller-Dialog
- Tinten-Detail zeigt zusätzlich Füllstand-Prozent, Ampelstatus und Nachkaufempfehlung.
- Schreibproben-Dialog unterstützt Defaults für kontextnahes Öffnen.
- Release-Metadaten und Schema-Version auf 0.2.61 aktualisiert.
- Cache-Dateien werden vor dem Release-ZIP entfernt.

## Risikoentscheidungen

- `nib_change_events` wurde nicht übernommen, weil `pen_nib_setups` bereits die kanonische Federhistorie ist.
- Reinigung erzeugt keine automatische Tintenmengen-Reduktion, um doppelte Verbrauchsbuchungen zu vermeiden.

## Erwartete lokale GUI-Smokes

1. Füller öffnen → Detailansicht → Schreibprobe hinzufügen.
2. Mindestens zwei Schreibproben für einen Füller anlegen → Vergleich öffnen.
3. Feder im Füller bearbeiten → Federhistorie prüfen.
4. Tinte mit Flaschengröße und Restmenge öffnen → Füllstand-Ampel prüfen.
