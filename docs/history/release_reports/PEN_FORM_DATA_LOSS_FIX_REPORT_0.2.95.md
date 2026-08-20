# Release Report – FountainPen Manager v0.2.95

## Anlass

Beim Erfassen eines Füllers verschwanden numerische Eingaben nach dem Verlassen des Feldes beziehungsweise beim Wechsel zum nächsten Formular-Tab.

## Root-Cause

`LocalizedDoubleSpinBox.valueFromText()` und `validate()` erhielten von Qt den sichtbaren Text inklusive Präfix oder Suffix. Dadurch konnte der zentrale Zahlenparser Werte wie `143,00 mm`, `24,50 g`, `0,80 ml` oder `CHF 39.96` nicht zuverlässig als Zahl erkennen. Beim Fokuswechsel interpretierte Qt den Parse-Fehler als `0`.

## Korrektur

- Präfixe und Suffixe werden vor dem Zahlenparsing zentral entfernt.
- Einheiten `mm`, `g` und `ml` bleiben reine Darstellung und beeinflussen den gespeicherten Zahlenwert nicht.
- Währungspräfixe und -suffixe funktionieren über dieselbe Logik.
- Ungültige oder noch unvollständige Texte setzen einen zuvor bestätigten Wert nicht mehr stillschweigend auf `0` zurück.
- Die bestehende App-Locale-Logik für Punkt und Komma bleibt erhalten.

## Verifikation

- Reproduktion vor Fix: `123.40 mm` wurde nach `interpretText()` zu `0.00 mm`.
- Laufzeitprüfung nach Fix: Marke, Modell, Länge `143,00 mm`, Gewicht `24,50 g` und Volumen `0,80 ml` blieben über alle vier Füller-Tabs erhalten.
- Regressionstest: `tests/test_pen_numeric_input_persistence_0295.py`.
- Vollständige Testsuite: **250 Tests bestanden**.
- KILLCRITIC: **95 Invarianten × 1000 = 95.000 Prüfungen, 0 Findings**.
- Versionssynchronität: **0.2.95 vollständig synchron**.

## Release-Einschätzung

Der gemeldete reproduzierbare Datenverlust ist an der gemeinsamen Eingabekomponente behoben und damit nicht nur im Füllerdialog, sondern in allen betroffenen Zahlen- und Geldfeldern abgesichert.
