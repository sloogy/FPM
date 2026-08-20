# FPM v0.2.97 – UI-, Usability- und Systembewertung

## Gesamturteil

FPM v0.2.97 ist für den aktuellen Umfang als offlinefähige Desktop-Anwendung **releasefähig**. Das Dashboard, die Hilfe und die Dateneingabe wurden deutlich klarer und sicherer. Die größten verbleibenden Risiken liegen nicht in der Kernfunktion, sondern in einzelnen großen Dialogen, der Wartbarkeit sehr umfangreicher UI-Klassen und der noch engen Kopplung zwischen Oberfläche und Datenbank.

**UI-/Usability-Gesamtwertung: 8,2/10.**
**System-Gesamtwertung: 8,0/10.**
**Releasebewertung: 8,8/10 – freigabefähig mit klarer technischer Nacharbeitsliste.**

## Bewertungsmatrix

| Bereich | Bewertung | Einordnung |
|---|---:|---|
| Visuelle Klarheit | 8,5/10 | Kachel-Dashboard und fokussierte Detailansicht sparen Platz |
| Laptop- und Fenstermodus | 7,8/10 | Hauptfenster gut; einzelne Dialoge bleiben groß |
| Auffindbarkeit | 8,7/10 | Suche, kontextbezogene Hilfe und direkter Handbuchzugriff |
| Dateneingabe und Fehlerschutz | 9,0/10 | Werte bleiben erhalten; Warnung vor Verwerfen |
| ADHS-freundliche Bedienung | 8,6/10 | klare Fokussierung, reduzierte gleichzeitige Information |
| Barrierefreiheit | 6,8/10 | einige graue Sekundärtexte haben zu wenig Kontrast |
| Architektur | 7,6/10 | gute Modultrennung, aber UI und Persistenz teils eng gekoppelt |
| Test- und Releaseprozess | 9,0/10 | 260 Tests, GUI-Smoke, i18n- und Release-Audits |
| Wartbarkeit | 6,9/10 | mehrere sehr große Klassen und Methoden |
| Daten- und Systemsicherheit | 8,5/10 | lokale Datenhaltung, Validierungen und sichere Release-Prüfung |

## UI- und Usability-Bewertung

### Stärken

1. **Platzsparendes Dashboard**
   - Die wichtigsten Informationen erscheinen zuerst als Textkacheln.
   - Ein Klick fokussiert genau einen Bereich und erweitert nur dessen Tabelle.
   - Ein Doppelklick führt direkt in das passende Modul.
   - Der Nutzer wird nicht mit mehreren großen Tabellen gleichzeitig belastet.

2. **Gute Laptop-Anpassung des Hauptfensters**
   - Dashboard und Hauptinhalt sind scrollbar.
   - Kacheln brechen abhängig von der Breite um.
   - Das Fenster bleibt bis zur tatsächlichen Mindestgröße von ungefähr 772 × 546 bedienbar.
   - Bei 1.024 × 640 Pixeln ist die neue Hilfe vollständig nutzbar.

3. **Verbesserte Orientierung**
   - Einfach- und Expertenmodus reduzieren Komplexität.
   - Die Hilfe kann zum aktuellen Reiter geöffnet werden.
   - Die Wiki-Suche reduziert langes Durchklicken.
   - Alle drei Handbücher lassen sich direkt aus der Anwendung öffnen.

4. **Sichere Dateneingabe**
   - Eingaben bleiben beim Wechsel zwischen Formularseiten erhalten.
   - Lokalisierte Maße, Volumen, Gewicht und Währung werden korrekt verarbeitet.
   - Ungespeicherte Änderungen werden vor dem Verwerfen erkannt.

5. **Gute Fokusführung**
   - Im Dashboard bleibt nur eine Detailtabelle aktiv.
   - Der Tastaturfokus wird in die geöffnete Tabelle gesetzt.
   - Tastenkürzel und tabellenbezogene Löschaktionen sind vorhanden.

### Priorisierte UI-Findings

#### P1 – Große Dialoge noch nicht vollständig responsiv

Einige Dialoge verwenden weiterhin feste oder hohe Mindestmaße, beispielsweise:

- Federdialog mit mindestens ungefähr 640 Pixeln Höhe,
- Größenvergleich um 980 × 680,
- Füllerdialog um 720 × 600,
- Schreibprobenvergleich um 900 × 520.

Auf Displays mit 1.024 × 600, hoher Betriebssystemskalierung oder großen Schriftarten kann der untere Bereich knapp werden.

**Empfehlung:** Eine zentrale `ResponsiveDialogGeometry`-Hilfsfunktion einführen, die Startgröße und Mindestgröße gegen den verfügbaren Bildschirmbereich begrenzt und bei Bedarf einen Scrollbereich aktiviert.

#### P1 – Einstellungen werden auf sehr schmalen Fenstern eng

Die Hauptnavigation, die Einstellungen-Navigation und mehrere Mindestbreiten addieren sich. Bei ungefähr 800 Pixeln Fensterbreite kann Inhalt stark zusammengedrückt oder Text abgeschnitten werden.

**Empfehlung:** Die Einstellungsnavigation unter einer Breitschwelle in eine ComboBox oder ein ausklappbares Menü umwandeln und Mindestbreiten von großen Buttons entfernen.

#### P2 – Viele Hilfe-Reiter auf kleinen Displays

Die Hilfe besitzt neun Themenreiter. Bei 800 × 600 erscheinen horizontale Pfeile und die letzten Reiternamen sind nicht gleichzeitig sichtbar.

**Empfehlung:** Unter etwa 900 Pixeln Breite eine vertikale Themenliste oder eine kompakte Themenauswahl verwenden.

#### P2 – Kontrast einzelner Sekundärtexte

Im übrigen UI kommen noch häufig helle Grautöne vor. Gemessene Kontraste auf weißem Hintergrund:

- `#7f8c8d`: ungefähr 3,48:1
- `#95a5a6`: ungefähr 2,56:1
- neuer Hilfetext `#5f6f72`: ungefähr 5,25:1

Die ersten beiden Werte sind für normalen Text teilweise zu niedrig.

**Empfehlung:** Eine zentrale barriereärmere Farbpalette definieren und Sekundärtext mindestens auf ungefähr `#5f6f72` oder einen thematisch gleichwertigen Kontrastwert anheben.

#### P2 – Doppelklick ist nicht für alle Nutzer offensichtlich

Der Doppelklick auf eine Dashboard-Kachel ist effizient, aber ohne Dokumentation nicht unmittelbar erkennbar.

**Empfehlung:** In der erweiterten Detailansicht zusätzlich eine sichtbare Aktion „Im Reiter öffnen“ anbieten. Der Doppelklick bleibt als Schnellweg erhalten.

#### P2 – Toolbar bei 800 Pixeln Breite

Bei sehr schmalem Fenster wird der Suchbereich in der Toolbar verkürzt. Die Funktion bleibt vorhanden, die Beschriftung ist jedoch weniger klar.

**Empfehlung:** Responsive Toolbar mit Überlaufmenü und Symbolmodus für schmale Fenster.

## System- und Architekturprüfung

### Kennzahlen

| Kennzahl | Wert |
|---|---:|
| Python-Dateien | 113 |
| Produktionsdateien | 74 |
| Testdateien | 39 |
| Gesamtzeilen | ca. 30.271 |
| Produktionszeilen | ca. 26.359 |
| Testzeilen | ca. 3.912 |
| Funktionen/Methoden | ca. 1.386 |
| Klassen | 114 |
| Breite Exception-Handler | 163 |
| TODO/FIXME/HACK | 0 |

### Systemstärken

- Saubere grobe Trennung in `ui`, `logic`, `database`, `i18n` und `updater`.
- Offlinefähige SQLite-/SQLAlchemy-Basis.
- Lazy Loading der Hauptmodule reduziert Startlast.
- Ereignisbus für modulübergreifende Aktualisierungen.
- Zentrale Versionssynchronisierung.
- Umfangreiche i18n-Prüfung für Deutsch, Englisch und Französisch.
- Cross-Platform-Buildstruktur für Windows und Linux.
- GUI-Smoke-Test und automatisierte Release-Audits.
- Keine offenen TODO-, FIXME- oder HACK-Markierungen.
- Lokale Medien- und Pfadprüfungen sowie abgesicherte Update-Metadaten.

### Priorisierte System-Findings

#### P1 – UI greift teilweise direkt auf Datenbanksitzungen zu

Mehrere Widgets enthalten Datenbanktransaktionen, Importlogik und fachliche Verarbeitung. Dadurch sind Oberfläche, Business-Logik und Persistenz nicht überall sauber getrennt.

**Risiko:** Änderungen werden schwerer testbar; Fehlerbehandlung und Transaktionen verteilen sich über viele UI-Dateien.

**Empfehlung:** Schrittweise Repository- und Service-Schicht einführen. Neue Funktionen sollten nicht mehr direkt aus Widgets auf `get_session()` zugreifen.

#### P1 – Sehr große UI-Klassen

Besonders groß sind unter anderem:

- `PenWidget`: ungefähr 1.253 Zeilen,
- `RotationEngine`: ungefähr 912 Zeilen,
- `SettingsWidget`: ungefähr 814 Zeilen,
- `PenDialog`: ungefähr 707 Zeilen,
- `DashboardWidget`: ungefähr 688 Zeilen.

Einzelne Methoden sind ebenfalls sehr lang, etwa `DashboardWidget.refresh()` mit über 300 Zeilen.

**Risiko:** Hohe Änderungsgefahr, schwierige Reviews und mehr Seiteneffekte.

**Empfehlung:** Tabellenmodelle, Dialogseiten, Importdienste und Dashboard-Sektionen in eigene Komponenten auslagern.

#### P2 – Breite Exception-Behandlung

Es existieren ungefähr 163 breite `except Exception`- oder vergleichbare Handler.

**Risiko:** Interne Programmierfehler können als allgemeine Nutzerfehlermeldung erscheinen oder nur im Log sichtbar werden.

**Empfehlung:** An Systemgrenzen breite Handler beibehalten, intern jedoch gezielte Exception-Typen verwenden und unerwartete Fehler mit Kontext erneut auslösen oder zentral melden.

#### P2 – Navigation über feste Indizes

Ein Teil der Navigation verwendet feste Seitenindizes und parallele Zuordnungstabellen.

**Risiko:** Beim Einfügen oder Ausblenden neuer Reiter können falsche Ziele entstehen.

**Empfehlung:** Eine zentrale `PageId`-Enumeration beziehungsweise Registry für Navigation, Hilfe, Berechtigungen und Einfach-/Expertenmodus verwenden.

#### P2 – Keine gemessene Testabdeckung

Die Anzahl der Tests ist hoch, aber es gibt noch keinen verbindlichen Coverage-Wert. Einige Tests sind statische Quelltextprüfungen statt vollständiger Verhaltenstests.

**Empfehlung:** `pytest-cov` einführen, zunächst Bericht ohne harte Schranke, anschließend einen realistischen Mindestwert für Logik- und Servicecode festlegen.

#### P2 – Statische Analyse ausbaufähig

Ruff, MyPy oder vergleichbare Werkzeuge sind noch nicht als verpflichtende CI-Schritte konfiguriert.

**Empfehlung:** Zuerst Ruff mit konservativem Regelsatz einführen; Typprüfung danach modulweise für neue Service- und Repository-Schnittstellen aktivieren.

#### P3 – Eigene Schema-Migrationen wachsen mit

Die SQLite-Migrationen werden derzeit projektintern verwaltet. Das ist für den heutigen Umfang funktionsfähig, wird bei häufigeren Schemaänderungen aber schwerer nachvollziehbar.

**Empfehlung:** Entweder eine explizite versionierte Migrationsregistry ausbauen oder mittelfristig Alembic integrieren.

#### P3 – Große i18n-Kompatibilitätsschicht

`i18n/qt_i18n.py` ist mit ungefähr 1.150 Zeilen weiterhin umfangreich und enthält historische Kompatibilitätslogik.

**Empfehlung:** Mit jeder bearbeiteten Oberfläche weitere Legacy-Zuordnungen durch explizite sprechende Schlüssel ersetzen.

## Releaseprüfung

| Prüfung | Ergebnis |
|---|---:|
| Automatisierte Tests | 260 bestanden |
| GUI-Smoke-Test | bestanden |
| Python-Kompilierung | bestanden |
| Versionsabgleich | bestanden |
| i18n-Audit | 2.089 Schlüssel × 3 Sprachen |
| i18n-Qualität | 0 Findings |
| KILLCRITIC | 104.000 Checks, 0 Findings |

## Releaseentscheidung

**Freigabe empfohlen.** Es wurden keine funktionalen Releaseblocker gefunden. Die Version ist für den aktuellen Enthusiasten- und Sammlungsumfang stabil genug. Die nächste technische Schwerpunktversion sollte nicht erneut viele neue Funktionen aufnehmen, sondern vorrangig folgende drei Themen bearbeiten:

1. responsive Geometrie für alle Dialoge und Einstellungen,
2. Zerlegung der großen UI-Klassen und Einführung einer Service-/Repository-Schicht,
3. zentrale barriereärmere Farbpalette und ergänzende Coverage-/Lint-Prüfungen.
