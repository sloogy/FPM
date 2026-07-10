# Release Report – FountainPen Manager v0.2.78

**Basis:** v0.2.77 Quick Actions / Mode Logic Hardening  
**Build:** online-dimensions-lookup  
**Datum:** 7. Juli 2026

## Kritischer Befund

Die bisherige „Cache/Web“-Funktion war funktional irreführend: Sie konnte nur lokale Cache-Treffer übernehmen. Ohne Treffer öffnete sie technische Websuche und Bildsuche im Browser, erzeugte aber keinen strukturierten Vorschlag für die Eingabefelder.

## Umsetzung

- `logic/pen_dimensions_service.py` erweitert um einen optionalen Online-Lookup.
- Der Lookup lädt eine allgemeine Suchseite und bis zu vier Kandidatenseiten, extrahiert Plaintext und sucht nach beschrifteten Werten mit Einheit.
- Parser validiert plausible Bereiche, z. B. Länge in mm/cm/in, Gewicht in g, Kapazität in ml/cc.
- `ui/pen_widget.py` ruft den Lookup jetzt mit `allow_online=True` auf.
- Online-Vorschläge werden im bestehenden Bestätigungsdialog angezeigt und nach Annahme in `pen_dimensions_cache.json` gemerged.
- Browser-Fallback bleibt erhalten, falls kein sicherer Treffer gefunden wird.
- I18N `de/en/fr` angepasst.

## Geprüft

```text
python -m pytest tests/test_pen_dimensions_service.py -q
→ 11 passed

python -m pytest -q
→ 148 passed

python tools/sync_version.py --check
→ Alle Versionsdateien synchron: 0.2.78
```

## Releasefähigkeit

**Einschätzung:** releasefähig für v0.2.78, mit bewusst konservativer Online-Extraktion.  
Nicht garantiert wird, dass jede Shop-/Herstellerseite auslesbar ist; unsichere Treffer werden absichtlich nicht vorgeschlagen.
