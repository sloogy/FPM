# v0.2.38 Tour Abort Hotfix

## Behoben

- Die App-Tour hat jetzt jederzeit einen klar sichtbaren Button **✕ Tour abbrechen** oben rechts.
- Die Tour kann zusätzlich mit **Esc** beendet werden.
- Die Bubble bleibt in interaktiven Schritten bedienbar, auch wenn das Overlay Klicks an die App darunter durchlässt.
- Der bestehende Tour-Start aus Hilfe und Einstellungen bleibt erhalten.

## Technische Änderung

`TourBubble` und der neue Abbruch-Button sind nun Geschwister des Overlays statt Kinder des Overlays. Dadurch verhindert `WA_TransparentForMouseEvents` nicht mehr, dass die Tour-Navigation bedient werden kann.
