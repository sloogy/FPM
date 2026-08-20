# FPM v0.2.98 – Enterprise-, UI- und Usability-Audit

## 1. Management Summary

FountainPen Manager v0.2.98 ist im geprüften Umfang **releasefähig**. Die zuvor priorisierten Laptop-, Dialog-, Kontrast- und Dashboard-Probleme sind behoben. Während der Gegenprüfung wurden zusätzlich vier reale Fehler gefunden und korrigiert: offene Datenbankverbindungen, eine fehlerhaft verdrahtete Dashboard-Übersetzung, ein falscher initialer Dashboard-Reflow und veraltete Release-Testmetadaten.

**Releaseblocker: 0**
**Offene kritische Fehler: 0**
**Offene hohe technische Risiken: 2, beide nicht unmittelbar releaseblockierend**

### Bewertung

| Bereich | Wertung | Urteil |
|---|---:|---|
| UI-Qualität | **9,0/10** | klar, responsiv und laptopgeeignet |
| Usability | **9,1/10** | sehr gute Fokusführung und Fehlerschutz |
| Barrierearme Darstellung | **8,5/10** | Kontrast deutlich verbessert; kein vollständiger Accessibility-Test |
| Funktionsstabilität | **9,2/10** | 267 Tests und GUI-Smoke grün |
| Datenhaltung | **8,8/10** | stabiler SQLite-/SQLAlchemy-Lebenszyklus |
| Architektur/Wartbarkeit | **7,6/10** | modularer Aufbau, aber große UI-Klassen und direkte DB-Zugriffe |
| Test-/Releaseprozess | **9,2/10** | Coverage-Baseline, Ruff, i18n, KILLCRITIC und Cross-Platform-CI |
| Enterprise-Gesamtwertung | **8,6/10** | geeignet für den aktuellen Offline-Desktop-Einsatz |
| Releasefähigkeit | **9,3/10** | **Freigabe empfohlen** |

## 2. Geprüfter Umfang

- Python- und Qt-Quellcode
- SQLite-/SQLAlchemy-Datenhaltung
- Füller-, Tinten-, Feder-, Papier-, Rotation-, Regel-, Ausgaben-, Wishlist- und Hilfe-Module
- Dashboard und Einstellungen bei Laptop-/Schmalfenstergrößen
- Große Erfassungs- und Vergleichsdialoge
- Deutsch, Englisch und Französisch
- Release-Metadaten, Windows-/Linux-Buildpfade und Updater-Assets
- Statische Fehlerklassen, GUI-Smoke-Test, Regressionstests und Coverage

Nicht Bestandteil eines vollwertigen Penetrationstests waren externe Infrastruktur, GitHub-Kontoabsicherung, Betriebssystem-Härtung und reale Netzwerk-Manipulation.

## 3. Kennzahlen

| Kennzahl | Ergebnis |
|---|---:|
| Python-Dateien | 114 |
| Produktionsdateien | 74 |
| Testdateien | 40 |
| Produktionszeilen | ca. 26.698 |
| Testzeilen | ca. 4.080 |
| Klassen | 103 |
| Funktionen/Methoden | ca. 1.095 |
| breite Exception-Handler | 163 |
| TODO/FIXME/HACK | 0 |
| automatisierte Tests | 267 bestanden |
| i18n-Schlüssel | 2.091 × 3 Sprachen |
| KILLCRITIC | 104.000 Checks, 0 Findings |
| ausgewählte Coverage | 54 % |

## 4. Gefundene und behobene Fehler

### ENT-001 – Datenbankverbindungen blieben offen

**Schweregrad:** Hoch
**Status:** Behoben

Wiederholte Initialisierung, Datenbankwechsel und das reguläre Programmende konnten SQLAlchemy-Sessions beziehungsweise SQLite-Handles offenlassen. Dies erhöht auf Windows das Risiko blockierter Datenbankdateien und erschwert Backup, Restore und Pfadwechsel.

**Korrektur:**

- zentraler, idempotenter `close_db()`-Lebenszyklus,
- `close_all_sessions()` und `engine.dispose()`,
- Rücksetzen globaler Engine-/SessionFactory-Referenzen,
- Aufruf vor Initialisierung und Reinitialisierung,
- Aufruf über `QApplication.aboutToQuit`,
- sichere SQLite-Context-Manager in der Wartungsfunktion,
- eigener Regressionstest.

### UI-001 – Große Dialoge überschritten kleine Arbeitsflächen

**Schweregrad:** Hoch
**Status:** Behoben

Feste Start- und Mindestgrößen konnten bei hoher DPI-Skalierung oder niedriger Displayhöhe Schaltflächen außerhalb des sichtbaren Bereichs platzieren.

**Korrektur:** Zentrale `ResponsiveDialog`-Basis mit Bildschirmbegrenzung, Scrollbereich und erreichbarer Aktionsleiste. Sie wird projektweit für große Erfassungs-, Import-, Vergleichs-, Update- und Einstellungsdialoge verwendet.

### UI-002 – Einstellungen auf schmalen Fenstern zu eng

**Schweregrad:** Hoch
**Status:** Behoben

Die linke Einstellungsnavigation und feste Aktionsbreiten nahmen zu viel horizontalen Raum ein.

**Korrektur:**

- kompakte Auswahlbox bei schmaler Breite,
- Wechsel bereits bei 800-Pixel-Ansicht sichtbar,
- responsive 1/2/3-Spalten-Aktionsgruppen,
- umbrechende Formulare,
- entfernte unnötige Mindestbreiten.

### A11Y-001 – Zu geringer Kontrast von Sekundärtexten

**Schweregrad:** Mittel bis hoch
**Status:** Behoben

Helle Grautöne wie `#95a5a6` lagen auf Weiß deutlich unter 4,5:1.

**Korrektur:** Normale Sekundärtexte verwenden zentral `#5f6f72`. Der gemessene Kontrast auf Weiß liegt bei ungefähr 5,25:1 und erfüllt damit WCAG AA für normalen Text.

### UX-001 – Dashboard-Navigation nur über Doppelklick erkennbar

**Schweregrad:** Mittel
**Status:** Behoben

Doppelklick war effizient, aber nicht selbsterklärend.

**Korrektur:** Jede Kachel besitzt eine sichtbare, lokalisierte Aktion **„Im Reiter öffnen“**. Einfachklick und Doppelklick bleiben zusätzlich erhalten.

### I18N-001 – Übersetzungsschlüssel statt Beschriftung sichtbar

**Schweregrad:** Hoch
**Status:** Behoben

Die neue Dashboard-Schaltfläche war zunächst als flacher JSON-Schlüssel gespeichert. Da der Translator verschachtelte Pfade auflöst, erschien im visuellen Test `dashboard.tiles.open_tab`.

**Korrektur:** Schlüssel in die verschachtelte `dashboard.tiles`-Struktur verschoben und Laufzeittest ergänzt.

### UI-003 – Dashboard blieb beim ersten Anzeigen im falschen Reflow

**Schweregrad:** Mittel
**Status:** Behoben

Die `QScrollArea` meldete ihre endgültige Viewport-Breite erst nach dem ersten Layoutdurchlauf. Dadurch konnten Schnellaktionen trotz breitem Fenster einspaltig bleiben.

**Korrektur:** Sofortiger plus verzögerter zweiter Reflow in `resizeEvent` und `showEvent`; Regressionstest prüft die tatsächliche Grid-Position.

### REL-001 – Release-Testmetadaten noch auf v0.2.97

**Schweregrad:** Hoch für den Releaseprozess
**Status:** Behoben

Zwei Tests erwarteten den vorherigen Versions- beziehungsweise Buildnamen und blockierten den vollständigen Release-Lauf.

**Korrektur:** Runtime-Asset-Test und Metadatenprüfung auf v0.2.98 synchronisiert.

## 5. UI-Audit

### Positiv

- Kachel-Dashboard zeigt die wichtigsten Informationen zuerst als Text.
- Detailtabellen werden exklusiv und fokussiert geöffnet.
- Sichtbare Öffnen-Schaltflächen ergänzen den Doppelklick.
- Dashboard und Hauptinhalte sind scrollbar.
- Kachel- und Schnellaktionsraster reagieren nach dem tatsächlichen Viewport.
- Große Dialoge bleiben innerhalb der verfügbaren Arbeitsfläche.
- Einstellungen nutzen bei schmaler Breite eine kompakte Navigation.
- Sekundärtexte besitzen nun ausreichenden Normaltext-Kontrast.
- In-App-Wiki, kontextbezogene Hilfe und Handbücher sind dreisprachig.

### Verbleibende UI-Punkte

#### UI-R01 – Toolbar bei extrem schmalen Fenstern

Bei ungefähr 800 Pixeln Gesamtfensterbreite können Haupttoolbar und Suchfeld weiterhin verdichtet wirken. Die Funktionen bleiben erreichbar, aber ein Überlaufmenü oder Symbolmodus wäre langfristig klarer.

**Priorität:** P2, nicht releaseblockierend.

#### UI-R02 – Hilfe-Themenauswahl bei sehr geringer Breite

Viele Hilfe-Themen erzeugen auf kleinen Displays Scrollpfeile in der Reiterleiste. Die Wiki-Suche kompensiert dies weitgehend.

**Priorität:** P2.

#### UI-R03 – Vollständige Accessibility-Prüfung fehlt

Kontrast und Größenverhalten wurden geprüft. Noch offen sind systematische Screenreader-, High-Contrast-, reine Tastatur- und vergrößerte-Schrift-Tests.

**Priorität:** P2.

## 6. Usability-Audit

### Stärken

- ADHS-freundliche Reduktion gleichzeitig sichtbarer Informationen.
- Einfach- und Expertenmodus begrenzen Komplexität.
- Direkte Schnellaktionen für häufige Aufgaben.
- Schutz vor Verwerfen ungespeicherter Füllerdaten.
- Maße, Gewicht, Volumen und Währung bleiben beim Seitenwechsel erhalten.
- Suche, Filter, Kontextmenüs und direkte Modulnavigation reduzieren Klickwege.
- Warnungen informieren, blockieren aber nicht unnötig; Overrides bleiben möglich.
- Wiki-Suche und kontextbezogene Hilfe reduzieren Orientierungsverlust.

### Verbleibende Usability-Punkte

- Einige Fachdialoge enthalten weiterhin viele Felder; progressive Offenlegung könnte die Erstnutzung weiter vereinfachen.
- Einzelne Expertenfunktionen sind nur über Kontextmenüs auffindbar.
- Ein konsistentes Undo-System für Lösch- und Massenaktionen wäre langfristig stärker als reine Bestätigungsdialoge.

## 7. Enterprise- und Systemaudit

### Stärken

- Grobe Trennung in `ui`, `logic`, `database`, `i18n` und `updater`.
- Lokale, offlinefähige SQLite-Datenhaltung.
- Kontrollierter Datenbank-Lebenszyklus.
- Keine Verwendung von `shell=True`, produktivem `eval()` oder produktivem `exec()` gefunden.
- Update-Downloads verwenden Timeouts und Release-Assets werden per SHA256 geprüft.
- Windows- und Linux-Onedir-Builds werden aus demselben Tag erstellt.
- Versions- und Pfadprüfungen sind in CI integriert.
- CI erzwingt jetzt kritische Ruff-Regeln sowie eine Coverage-Untergrenze von 50 % für Logik, Datenbank und Updater.
- Umfangreiche i18n- und KILLCRITIC-Prüfungen.

### Offene technische Risiken

#### ENT-R01 – Niedrige Abdeckung kritischer Entscheidungslogik

Gesamtbaseline: 54 %. Besonders niedrig:

- `logic/rotation_engine.py`: 23 %
- `logic/rule_engine.py`: 21 %
- `logic/auto_mode_service.py`: 38 %
- Updater-Module: 0 % in der gemessenen Suite

**Risiko:** Änderungen an Rotation, Regeln und Updatepfaden können regressieren, obwohl die Gesamtsuite grün bleibt.

**Priorität:** P1 technische Nacharbeit.
**Empfehlung:** Verhaltens- und Fehlerpfadtests zuerst für Regel- und Rotationsengine, danach isolierte Updater-Tests mit temporären Verzeichnissen und simulierten Manifesten.

#### ENT-R02 – Große, eng gekoppelte UI-Klassen

- `PenWidget`: ca. 1.253 Zeilen
- `SettingsWidget`: ca. 847 Zeilen
- `PenDialog`: ca. 711 Zeilen
- `DashboardWidget`: ca. 699 Zeilen
- `DashboardWidget.refresh()`: ca. 309 Zeilen

15 UI-Dateien greifen direkt auf `get_session()` zu.

**Risiko:** Hohe Seiteneffekt- und Review-Komplexität.

**Priorität:** P1 technische Nacharbeit, nicht unmittelbarer Releaseblocker.
**Empfehlung:** Repository-/Service-Schicht, Tabellenmodelle und getrennte Dialogseiten schrittweise einführen.

#### ENT-R03 – Breite Exception-Handler

163 breite Handler bleiben vorhanden. Viele sind sinnvolle UI-/Systemgrenzen, andere können Programmierfehler verdecken.

**Priorität:** P2.
**Empfehlung:** Bei jeder bearbeiteten Funktion gezielte Ausnahmen verwenden und unerwartete Fehler mit Kontext zentral protokollieren.

#### ENT-R04 – Supply-Chain-Reproduzierbarkeit

Laufzeitabhängigkeiten besitzen Mindestversionen, aber keine vollständig gelockten, gehashten Release-Abhängigkeiten.

**Priorität:** P2.
**Empfehlung:** Für offizielle Builds einen geprüften Lock-/Constraints-Stand erzeugen; automatische Dependency-Updates getrennt testen.

#### ENT-R05 – Navigation über feste Indizes

Teile der Navigation, Hilfe und Modi verwenden Seitenindizes.

**Priorität:** P2.
**Empfehlung:** zentrale `PageId`-/Registry-Struktur einführen.

## 8. Release- und Qualitätsprüfung

| Prüfung | Ergebnis |
|---|---:|
| Python-Kompilierung | bestanden |
| automatisierte Tests | 267 bestanden |
| GUI-Smoke-Test | bestanden |
| kritische Ruff-Regeln | bestanden |
| Versionssynchronisierung | bestanden |
| Windows-sichere Pfade | bestanden |
| i18n-Audit | 2.091 Schlüssel × 3 Sprachen |
| i18n-Qualität/Wiring/Runtime | bestanden |
| KILLCRITIC | 104.000 Checks, 0 Findings |
| Coverage-Gate | 54 %, Mindestwert 50 % bestanden |
| visuelle Stichproben | Dashboard, Einstellungen und Füllerdialog bestanden |

## 9. Releaseentscheidung

**FREIGABE EMPFOHLEN.**

Die gefundenen funktionalen und releasekritischen Fehler sind behoben. Die verbleibenden Punkte sind technische Schulden beziehungsweise zusätzliche Qualitätsausbaustufen. Sie verhindern den vorgesehenen Einsatz als lokale Desktop-Anwendung nicht, sollten aber vor einer starken Funktionsausweitung priorisiert werden.

### Empfohlene Reihenfolge für die nächste Härtungsrunde

1. Rotation-, Regel- und Updater-Coverage erhöhen.
2. `PenWidget`, `DashboardWidget` und `SettingsWidget` in kleinere Komponenten zerlegen.
3. Direkte Datenbankzugriffe aus UI-Widgets in Services/Repositorys verlagern.
4. Toolbar-/Hilfe-Navigation für extrem schmale Fenster weiter verdichten.
5. Vollständige Tastatur-, Screenreader- und High-Contrast-Prüfung durchführen.
