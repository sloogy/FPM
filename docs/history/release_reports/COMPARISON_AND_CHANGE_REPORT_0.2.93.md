# FountainPen Manager 0.2.94 – Vergleichs- und Änderungsbericht

## Vergleich 0.2.91 zu 0.2.92

0.2.92 ist die vollständigere Ausgangsbasis. Sie enthält gegenüber 0.2.91 zusätzliche Locale-/Währungs-Härtung, lokalisierte Eingabekomponenten und passende Regressionstests. Es gab in 0.2.91 keine bessere Funktionsvariante, die in 0.2.92 fehlte.

Wesentliche Erweiterungen von 0.2.92:
- lokalisierte Zahlen- und Währungseingaben
- zusätzliche Locale-/Currency-Tests
- Anpassungen an Tinten-, Füller-, Papier-, Ausgaben-, Wishlist- und Schreibproben-UI
- aktualisierte Übersetzungs- und Release-Artefakte

## Gefundene Skalierungsprobleme

1. Doppelte DPI-Skalierung: Qt liefert Bildschirmgeometrien bereits in logischen Pixeln. Die Anwendung multiplizierte zusätzlich mit `logicalDotsPerInch()/96`.
2. Starre Mindestgröße: `1100 × 680` wurde zusätzlich skaliert und konnte größer als die verfügbare Arbeitsfläche werden.
3. Starre Startgröße: `1360 × 820` wurde ebenfalls skaliert, ohne Begrenzung auf die Bildschirmfläche.
4. Fenstermodus reagierte nicht sauber auf einen Bildschirmwechsel.
5. Auto-Modus vergrößerte kleine Arbeitsflächen, obwohl dort eine kompaktere Darstellung nötig ist.

## Änderungen in 0.2.94

- Qt-konforme Skalierungslogik ohne zweite DPI-Multiplikation
- Auto-Skalierung anhand der logischen Arbeitsfläche
- kleine Bildschirme werden moderat kompakter statt größer
- Presets auf 0.90 / 1.00 / 1.12 / 1.28 bereinigt
- responsive Mindest- und Startgröße des Hauptfensters
- Begrenzung auf die verfügbare Bildschirmfläche inklusive Desktop-Leisten
- erneute Anpassung beim Wechsel auf einen anderen Monitor
- bestehende Locale-/Currency-Härtung vollständig übernommen
- Versions- und Installer-Metadaten auf 0.2.94 synchronisiert
- neue Regressionstests für DPI-Doppelskalierung und Fensterbegrenzung
- Cache-, Bytecode- und Testartefakte aus dem Paket entfernt

## Prüfung

- Python-Syntaxprüfung: bestanden
- vollständige Testsuite: **246 bestanden**
- neue Skalierungstests: bestanden
- Locale-/Currency-Tests: bestanden

## Verbleibende manuelle Prüfung

Ein echter visueller Test unter Windows und Linux mit mehreren DPI-Stufen ist weiterhin sinnvoll, insbesondere:
- 1366 × 768 bei 100 % und 125 %
- 1920 × 1080 bei 100 %, 125 % und 150 %
- Wechsel zwischen zwei Monitoren mit unterschiedlicher Skalierung
- maximiert, Fenstermodus und Rückkehr aus maximiert

Die automatischen Prüfungen konnten die PySide6-GUI in dieser Umgebung nicht visuell rendern; die zugrunde liegende Größen- und Skalierungslogik ist jedoch regressionsgetestet.
