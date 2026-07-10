# Changelog 0.2.78 – Online Dimensions Lookup

**Datum:** 7. Juli 2026  
**Build:** online-dimensions-lookup

## Behoben

- Die Füller-Dimensionsabfrage öffnet nicht mehr nur eine Browser-Suche, sondern kann echte strukturierte Online-Vorschläge erzeugen.
- Der Lookup sucht weiterhin zuerst im lokalen `pen_dimensions_cache.json`; nur ohne Cache-Treffer wird online gesucht.
- Online-Treffer werden konservativ aus Search-/Seitentext extrahiert: nur Werte mit klarer Beschriftung und Einheit werden übernommen.
- Unterstützte Vorschlagsfelder: Länge geschlossen, Länge offen, Länge gepostet, maximaler Durchmesser, Griffdurchmesser, Gewicht, Füllsystem und Füllvolumen.
- Bestätigte Online-Treffer werden in den lokalen Cache übernommen, damit spätere Bearbeitungen offline und reproduzierbar funktionieren.

## Sicherheit / Usability

- Keine automatische DB-Übernahme: Der Nutzer sieht die Werte und bestätigt aktiv.
- Bestehende gepflegte Felder werden nicht blind überschrieben; gefüllt werden nur leere bzw. nicht bewusst gesetzte Felder.
- Bei unsicherem oder fehlendem Online-Treffer bleiben die bisherigen manuellen Websuche-Links als Fallback erhalten.
- Deutsch, Englisch und Französisch wurden für den neuen Workflow nachgeführt.

## Tests

- Online-Parser mit HTML-/Tabellenbeispiel getestet.
- Online-Lookup über injizierten Fetcher getestet, damit die Tests netzwerkfrei bleiben.
- Guard-Test ergänzt, dass ohne `allow_online=True` kein Netzwerkzugriff passiert.
