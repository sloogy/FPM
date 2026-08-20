# FountainPen Manager v0.2.96 – Vergleich und Fokus-Kachel-Dashboard

## Vergleich der Ausgangsstände

Als Basis wurde **v0.2.95** beibehalten. Die zusätzlich hochgeladene **v0.2.92** ist für die Dashboard-Idee relevant, technisch aber älter.

| Bereich | v0.2.92 | v0.2.95 / Basis v0.2.96 |
|---|---|---|
| Locale und Währungen | vorhanden | vorhanden und weitergeführt |
| DPI-/Fensterskalierung | noch mit den später gefundenen Laptop-Problemen | responsive Arbeitsflächenbegrenzung aus v0.2.93 |
| Dashboard auf Laptop | dauerhaft hohe Inhalte | vollständige Scrollbarkeit und Umbruch aus v0.2.94 |
| Numerische Füllerdaten | Risiko des Rücksetzens bei Fokuswechsel | Datenerhalt aus v0.2.95 |
| Neue Kachelbedienung | nicht vorhanden | in v0.2.96 umgesetzt |

Eine Rückkehr auf v0.2.92 hätte die neueren Skalierungs- und Datenerhalt-Korrekturen entfernt. Deshalb wurde nur die gewünschte Dashboard-Idee neu umgesetzt und der vollständigere Kern beibehalten.

Der Dateivergleich bestätigt dies: v0.2.92 enthält **247** bereinigte Quelldateien, v0.2.95 **252**. Es gibt **keine Datei, die ausschließlich in v0.2.92 vorhanden ist**; v0.2.95 ergänzt fünf Dateien und verändert 26 gemeinsame Dateien. Damit musste aus v0.2.92 keine verlorene Funktion zurückgeführt werden.

## Bedienmodell

| Aktion | Verhalten |
|---|---|
| Einfachklick auf Kachel | Zugehörige Tabelle exklusiv öffnen, Kachel markieren, Tabellenfokus setzen und Tabelle in den sichtbaren Bereich scrollen |
| Erneuter Einfachklick | Tabelle einklappen |
| Klick auf andere Kachel | Bisherige Tabelle schließen und neue öffnen |
| Doppelklick auf Kachel | Direkt in den zugehörigen Reiter wechseln |
| Doppelklick auf Tabellenzeile | Ebenfalls in den zugehörigen Reiter wechseln |
| Enter/Leertaste | Kachel per Tastatur öffnen |
| Strg+Enter | Zugehörigen Reiter per Tastatur öffnen |

Einfach- und Doppelklick sind zeitlich getrennt. Ein Doppelklick klappt deshalb nicht zuerst unnötig die Tabelle auf.

## Kacheln und wichtigste Textinformationen

- **Sammlung & Zustand**: Anzahl Füller und Tinten, Sammlungswert, Hinweise und Archivstatus → Reiter **Statistiken**.
- **Rotation & Standzeit**: aktive Befüllungen, überfällige und bald fällige Befüllungen → Reiter **Rotation**.
- **Service & Sperren**: offene, kritische und gesperrte Fälle → Reiter **Füller**.
- **Letzte Aktivität**: Anzahl sichtbarer Aktivitäten und letzter Vorgang → Reiter **Rotation**.
- **Sparziele**: Anzahl, abgeschlossene Ziele und verbleibender Betrag; nur bei vorhandenen BudgetManager-Zielen → Reiter **Ausgaben**.

## Navigation im Einfachmodus

Statistiken und Ausgaben sind im Einfachmodus normalerweise ausgeblendet. Ein bewusster Doppelklick auf die entsprechende Dashboard-Kachel schaltet kontrolliert in den Expertenmodus und öffnet danach den richtigen Reiter. Damit führt der Doppelklick nicht still auf das Dashboard zurück.

## Platzersparnis und Laptop-Verhalten

- Im Grundzustand ist keine Detailtabelle geöffnet.
- Maximal eine Tabelle ist gleichzeitig sichtbar.
- Kacheln brechen abhängig von der Breite auf **3, 2 oder 1 Spalte** um.
- Die vollständige Dashboard-Scrollfläche und die responsive Fensterbegrenzung bleiben erhalten.
- Detailtabellen erhalten den Tastaturfokus und werden automatisch in den sichtbaren Bereich gerollt.

## Validierung

- Pytest: **254 bestanden**
- GUI-Smoke-Test mit Qt Offscreen: **bestanden**
- Visuelle Qt-Gegenprobe: **1080 × 700**, kompakter Zustand und geöffnete Detailtabelle geprüft
- i18n: **2.065 Schlüssel × 3 Sprachen**, alle Audits bestanden
- Versionssynchronität: **0.2.96**, bestanden
- Python-Compileall: bestanden
- KILLCRITIC: **100 Invarianten × 1.000 = 100.000 Prüfungen**, 0 Findings

## Release-Einschätzung

Der Quellstand ist als interner Testbuild freigabefähig. Native Windows- und Linux-Pakete müssen weiterhin über den vorhandenen Cross-Platform-Workflow gebaut und anschließend kurz auf einem realen Laptop geprüft werden.
