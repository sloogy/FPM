# FPM v0.2.23 P0/P1 Fixes

Basis: v0.2.22 stable-merge.

## P0 – Stabilität / Datenmodell

- Regel-Engine gehärtet:
  - blockierende/harde Regeln senken den Score stark, statt trotz Risiko oben zu erscheinen.
  - `nib_size_wetness` bleibt korrekt isoliert und wird robust gegen fehlende/falsche Werte geprüft.
  - JSON-Regelbedingungen werden defensiver ausgewertet.
  - zentrale Helfer für Nib-Text, Integer-Konvertierung und Blocker-Erkennung ergänzt.
- Datenbank-Migration ergänzt:
  - `pens.purchase_currency`
  - `pens.market_currency`
  - `pens.insurance_currency`
  - `pens.service_currency`
- `schema_version` auf `0.2.23` gesetzt.
- Doppelte `Ink`-Klassendeklaration in `models.py` entfernt.

## P1 – Usability / Regel-Erklärbarkeit

- Rotationsvorschläge enthalten jetzt zusätzlich `rule_warnings` als echte Liste.
- Why-Score-Dialog nutzt nicht mehr den zusammengebauten Tabellenstring, sondern echte Regelwarnungen.
- `rule_delta` zeigt nun die Regelwirkung relativ zur Basis 100, nicht mehr den kompletten internen Regel-Score.
- Blockierte Kombinationen bleiben theoretisch sichtbar/overridebar, werden aber stark herabgestuft.

## Bewusst nicht umgesetzt

- Papier in Rotation.
- Media-Modell.
- Undo/EventLog.
- vollständige i18n.

Diese Punkte bleiben P2/P3, weil sie separate Architekturentscheidungen benötigen.
