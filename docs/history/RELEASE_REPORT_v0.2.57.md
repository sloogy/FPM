# Release Report – FountainPen Manager v0.2.57

## Ergebnis

**Status: Release Candidate / Code-seitig releasefähig.**

Die vorhandene v0.2.56-Basis war syntaktisch und testseitig stabil. Ich habe die offenen Release-/Produktpunkte behoben, DAU-Freundlichkeit erweitert und zwei risikoarme, sinnvolle Sammlerfunktionen ergänzt.

## Behobene offene Punkte

1. **README veraltet**
   - Vorher: README meldete noch v0.2.55.
   - Jetzt: README, App-Metadaten und Release-Hinweise stehen auf v0.2.57.

2. **Release-Check unvollständig**
   - Vorher: GitHub Workflow prüfte nicht den sichtbaren Textaudit.
   - Jetzt: `i18n_visible_text_audit.py` ist im Workflow ergänzt.

3. **Fehlende kontrollierte BudgetManager-Schnittstelle**
   - Umsetzung: JSONL-Export aller Ausgaben über Einstellungen → Import / Export.
   - Sicherheitsentscheidung: kein direkter Zugriff auf die BudgetManager-DB.

4. **Dashboard war informativ, aber noch nicht handlungsorientiert genug**
   - Umsetzung: Sammlungs-Advisor mit priorisierten nächsten Schritten.

## Neue Funktionen

### Sammlungs-Advisor

Erkennt und priorisiert:

- überfällige aktive Befüllungen,
- aktive Tinten mit hohem Reinigungsrisiko,
- leere verfügbare Füller,
- gesperrte/Service-Füller,
- niedrige/leere Tintenstände,
- fast volles Papier,
- bald auslaufende Garantie,
- fehlende Fotos bei wertrelevanten Füllern,
- fehlende Wert-/Kaufpreisdaten.

### BudgetManager JSONL Export

Exportiert eine prüfbare Datei mit Manifest und stabilen Zeilen pro Ausgabe.
Die Struktur ist für spätere Upserts im BudgetManager geeignet und trennt die Programme sauber.

## Tests

```text
53 passed
compileall OK
i18n audit OK – 1581 Keys × 3 Sprachen
i18n quality OK
i18n key wiring OK
i18n runtime OK
i18n visible text OK
```

## Bewertung

| Bereich | Bewertung |
|---|---|
| Syntax / Importstruktur | OK |
| Unit-/Regressionstests | OK |
| i18n DE/EN/FR | OK |
| DAU-Führung | verbessert |
| Enthusiastenwert | verbessert |
| BudgetManager-Anbindung | kontrolliert vorbereitet |
| GUI-Laufzeit in Sandbox | nicht geprüft, PySide6 fehlt |
| Release als Quellpaket | OK |
| Release als gebaute EXE | noch lokal/GitHub zu bauen |

## Empfehlung

Für den nächsten Schritt lokal mit installierter PySide6-Umgebung starten und gezielt prüfen:

1. Dashboard → Sammlungs-Advisor sichtbar und lesbar.
2. Einstellungen → Import / Export → BudgetManager-JSONL exportieren.
3. Sprachwechsel DE/EN/FR bei Dashboard und Einstellungen.
4. Danach Tag `v0.2.57` setzen.
