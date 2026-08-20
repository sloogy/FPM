# FountainPen Manager v0.2.32 – Rules UI Hardening

## Ziel
Die Regeln-Seite war auf Laptop-Displays zu klein und zu überladen. Außerdem war Verbrauch/Restmenge nicht klar aktivierbar, weil Easy Mode die Funktion korrekt deaktiviert, die UI aber nicht klar zum Expert Mode geführt hat.

## Änderungen
- Regeln-Seite in Reiter aufgeteilt:
  - Zeiten
  - Auto Mode
  - Regelgruppen
  - Regelliste
- Eigene Scrollbereiche pro Reiter.
- Lesbarkeits-Skalierung direkt in der Regeln-Seite: Kompakt, Normal, Laptop groß, Sehr groß.
- Standardwert für Regeln-Ansicht: Laptop groß.
- Verbrauch/Restmenge ist im Easy Mode weiterhin aus.
- Verbrauch/Restmenge kann über einen Schnellbutton auf Expert Mode + Verbrauch aktiv gesetzt werden.
- Regelgruppen-Speichern schreibt nun auch den Bedienmodus, damit Expert Mode + Verbrauch wirklich in der Logik greift.
- Regelliste zeigt jetzt zusätzlich „Wirksam“, damit sichtbar ist, ob eine aktive Regel durch eine ausgeschaltete Gruppe trotzdem nicht greift.
- Doppelklick auf eine Regel toggelt aktiv/inaktiv.
- Regelliste hat Suche und Gruppenfilter.

## Wichtig
Easy Mode bleibt bewusst verbrauchsarm: keine automatische Restmengenbuchung.
Expert Mode erlaubt Verbrauch/Restmenge, wenn die Regelgruppe aktiviert ist.
