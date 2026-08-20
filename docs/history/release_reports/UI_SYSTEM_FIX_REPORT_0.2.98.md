# FPM v0.2.98 – UI- und System-Fixbericht

## Umgesetzter Fixumfang

### 1. Große Dialoge vollständig responsiv

Eine zentrale `ResponsiveDialog`-Basisklasse begrenzt Start-, Mindest- und Maximalgröße anhand der tatsächlich verfügbaren Bildschirmfläche. Umfangreiche Inhalte werden bei Bedarf in einen Scrollbereich gelegt. Direkte `QDialogButtonBox`-Aktionsleisten bleiben außerhalb des Scrollbereichs erreichbar.

Die Basis wird unter anderem von Füller-, Tinten-, Feder-, Papier-, Ausgaben-, Wishlist-, Schreibproben-, Regel-, Rotations-, Import-, Update- und Einstellungsdialogen verwendet. Der Bild-Zoom-Dialog behält seine bereits vorhandene bildabhängige Sonderlogik.

### 2. Einstellungen auf schmalen Fenstern

- Normale Breite: linke Seitenliste.
- Unterhalb der Breitschwelle: kompakte Auswahlbox oberhalb des Inhalts.
- Formulare umbrechen lange Zeilen.
- Datenbankpfad und Aktionsbereiche blockieren keine feste Mindestbreite mehr.
- Aktionsbuttons ordnen sich abhängig von der Breite in 1, 2 oder 3 Spalten an.

### 3. Kontrast von Sekundärtexten

Normale Sekundärtexte verwenden zentral `#5f6f72`. Auf weißem Hintergrund liegt der Kontrast bei ungefähr 5,25:1 und damit oberhalb der WCAG-AA-Schwelle von 4,5:1 für normalen Text. Frühere helle Grautöne wurden aus normalen Textkontexten entfernt.

### 4. Sichtbare Dashboard-Navigation

Jede Dashboard-Kachel enthält nun die lokalisierte Aktion **„Im Reiter öffnen“**. Sie führt direkt zum Zielmodul. Einfachklick zum Erweitern und Doppelklick als Schnellweg bleiben erhalten.

## Zusätzlich behobener Systemfehler

Datenbank-Sessions und Engine-Verbindungen konnten bei wiederholter Initialisierung oder beim Programmende offenbleiben. `database.db.close_db()` schließt nun alle Sessions, verwirft die Engine und setzt den globalen Zustand zurück. Der Ablauf wird bei Datenbankwechsel, Testende und `aboutToQuit` verwendet. Auch die direkte SQLite-Verbindung der Wartungsfunktion nutzt einen Context Manager.

## Regressionstests

Neue Tests prüfen:

- Dialogbegrenzung und Scrollbarkeit,
- Umschaltung der Einstellungsnavigation,
- responsiven Button-Reflow,
- sichtbare Dashboard-Öffnen-Schaltflächen und Navigation,
- Kontrastwert und Abwesenheit alter Textfarben,
- Verwendung der responsiven Dialogbasis,
- sauberen Datenbank-Lebenszyklus über die Gesamtsuite.

## Beim visuellen Audit zusätzlich behoben

- Die neue Dashboard-Schaltfläche war zunächst als flacher JSON-Schlüssel abgelegt und wurde zur Laufzeit als `dashboard.tiles.open_tab` angezeigt. Der Schlüssel ist nun korrekt in der verschachtelten i18n-Struktur verdrahtet und durch einen Laufzeittest abgesichert.
- Die tatsächliche Breite des `QScrollArea`-Viewports steht erst nach dem ersten Layoutdurchlauf fest. Ein verzögerter zweiter Reflow verhindert, dass Schnellaktionen und Kacheln nach dem Öffnen im falschen Einspaltenmodus bleiben.
- Die Breitschwelle der Einstellungen wurde so angepasst, dass die kompakte Navigation bei einer 800-Pixel-Ansicht sichtbar greift.
