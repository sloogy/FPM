# v0.2.35 – Nib Setup Workflow

## Ziel
Der Feder-Umbau ist jetzt dreistufig modelliert:

1. **NibFormat** = mechanischer Standard / Kompatibilität  
   Beispiel: Bock #6, JoWo #6, Pilot #10.
2. **Nib** = konkretes Feder-Exemplar / Tuning / Material / Schliff  
   Beispiel: Gravitas-getunte Bock #6 EF Stahl.
3. **PenNibSetup** = diese Feder in diesem Füller mit diesem Feed  
   Beispiel: Gravitas EF im Jinhao x750 mit Jinhao Feed, steiferer Eindruck.

## Änderungen
- Neues Modell `PenNibSetup` für Einbau-/Setup-Ebene.
- Migration erzeugt aktive Setups aus bestehenden `pen.nib_id`-Zuweisungen.
- Füller-Dialog fragt Feder und Setup direkt beim Füller ab.
- Feed/Flow/Setup-Steifigkeit/Setup-Feedback werden am Füller-Setup gespeichert, nicht mehr nur an der Feder.
- Beim Inline-Anlegen einer Feder wird ein vorhandenes ähnliches Exemplar angeboten, statt blind zu duplizieren.
- `NibFormat`-Suche normalisiert Schreibweisen wie `No.6`, `No 6`, `#6` teilweise.
- Regel-Engine und Rotation lesen bevorzugt `pen.active_nib_setup`.
- Wishlist-Federübernahme erzeugt nun direkt `NibFormat` + `Nib` statt nur Legacy-Felder.

## Warum
Eine Feder ist nicht nur Marke + Größe. Eine Bock #6 von Gravitas kann mechanisch in einen Jinhao x750 passen, aber wegen Feed/Gehäuse/Tuning anders schreiben. Genau diese Unterschiede gehören auf Setup-Ebene.

## Schema
- `schema_version` → `0.2.35`
