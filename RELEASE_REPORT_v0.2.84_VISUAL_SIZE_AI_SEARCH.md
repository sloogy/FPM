# Release Report v0.2.84 – Visual Size Comparison & AI Search

## Ergebnis

Die Version ist als Quellpaket releasefähig. Der gemeldete Größenvergleich wurde optisch und funktional ersetzt: Statt Balken werden nun stilisierte Füller gezeichnet, deren Länge aus den gespeicherten Maßen skaliert wird. Zusätzlich gibt es eine echte Überlagerungsansicht, damit Sammler Längenunterschiede direkt sehen können.

## Behobene Punkte

| Bereich | Vorher | Jetzt |
|---|---|---|
| Größenvergleich | horizontale Balken, wenig sammlerfreundlich | stilisierte Füller-Silhouetten |
| Vergleichslogik | nur einfache Balken je Maß | Overlay oder Liste |
| Maßwahl | geschlossen/offen/gepostet gleichzeitig schwer lesbar | gezielte Auswahl: bestes Maß, geschlossen, offen, gepostet |
| Bildrecherche | enge `site:`-Suche konnte falsche/zu wenige Treffer liefern | breite Google KI/Websuche + Google Images |
| Dimensionsrecherche | manueller Browserpfad begann mit Hersteller-`site:` | manueller Browserpfad ohne `site:`, Parser bleibt Hersteller-zuerst |

## Architekturentscheidung

Die manuelle Recherche und der automatische Parser sind nun klar getrennt:

- **Manuell:** breit, KI-/Google-freundlich, keine harte Domain-Einschränkung.
- **Automatisch:** konservativ, testbar, hersteller-zuerst, keine automatische Datenübernahme ohne Bestätigung.

Damit bekommt der Nutzer bessere Suchergebnisse im Browser, während die App weiterhin keine unsicheren Daten automatisch übernimmt.

## Tests

```text
python -m pytest -q -ra
192 passed

python -m compileall -q .
OK

python tools/sync_version.py --check
Alle Versionsdateien synchron: 0.2.84
```

## Bekannte Einschränkung

Der vollständige GUI-Smoke-Test benötigt PySide6. In der Sandbox ohne PySide6 kann nur statisch und über Unit-Tests geprüft werden.
