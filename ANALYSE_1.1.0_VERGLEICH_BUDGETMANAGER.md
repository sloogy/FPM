# FPM 1.1.0 — Stand und Vergleich mit BudgetManager (Design und Verhalten)

Verglichen wurde der Arbeitsstand von `sloogy/FPM` (Version 1.1.0, main bei
`8a5a7bc`, dazu die noch unveröffentlichten Commits im Changelog) mit
`sloogy/Budgetmanager` (Version 2.2.70). BudgetManager ist in dieser Suite die
Vorlage: Der gemeinsame Designkatalog, die Brücke, der Updater und die
Sicherheitsbausteine sind dort zuerst entstanden.

## Kurzurteil

Alles, was **zwischen** den Programmen liegt, ist deckungsgleich: Designkatalog,
Brückenformat, Updater, Dateirechte, Instanzsperre, Übersetzungsstand. Diese
Arbeit ist abgeschlossen und lässt sich Datei für Datei nachweisen.

Was **innerhalb** von FPM liegt, ist es nicht. FPM hat die Designprofile des
BudgetManagers übernommen, aber nicht dessen Weg, sie in die Oberfläche zu
bringen. Der BudgetManager führt jede Farbe über `views/ui_colors.py`; in seinen
56 View-Dateien steht **kein einziges** Farbliteral (die einzige Ausnahme,
`views/delegates/badge_delegate.py`, rechnet Schwarz oder Weiß aus der
Helligkeit der Fläche aus — das ist keine gesetzte Farbe, sondern Kontrast). FPM trägt weiterhin 228
Hex-Literale in 16 Widget-Dateien und gleicht sie zur Laufzeit über eine
Ersetzungstabelle aus (`ui/host_theme.py`). Diese Tabelle erfasst 186 der 228
Vorkommen. Die übrigen 42 bleiben in jedem Profil unverändert — und weil die
Vorder-, nicht aber die Hintergrundfarbe umgefärbt wird, entstehen daraus im
dunklen Profil belegbar unlesbare Stellen.

Beim Verhalten fehlt FPM vor allem die zentrale Bedienhärtung: Der
BudgetManager hängt einen Eventfilter in die `QApplication` und härtet damit
jeden Dialog, den es je geben wird. FPM macht dieselben Dinge von Hand, an
19 Stellen, und damit lückenhaft.

## Geprüfter Stand von FPM

Lokal mit Python 3.12 und echtem PySide6 6.11 ausgeführt:

| Prüfung | Ergebnis |
| --- | --- |
| `pytest` | 604 Tests, alle grün |
| `tools/design_sync.py check` | 26 Designs, 0 Beanstandungen |
| `tools/exception_audit.py` | 139 breite ≤ 139, 33 stumme ≤ 33, 0 nackte |
| `tools/db_access_audit.py` | 49 direkte UI-Queries ≤ 49 |
| `tools/name_audit.py` | 0 undefinierte Namen, 0 ungenutzte Importe |
| `tools/import_smoke.py` | 71 Module importierbar |
| `tools/sync_version.py --check` | alle Versionsdateien auf 1.1.0 |
| `tools/i18n_audit.py` | 2129 Schlüssel × 3 Sprachen |
| `tools/check_windows_paths.py` | keine Windows-ungültigen Pfade |

Der Stand ist also in sich sauber. Die Befunde unten sind keine Regressionen —
sie sind die Arbeit, die von der Angleichung an den BudgetManager noch offen
ist. Kein bestehendes Gate kann sie sehen, weil keines von ihnen prüft, ob eine
Farbe aus dem Profil kommt.

Randnotiz: Der Quelltext setzt Python 3.12 voraus (verschachtelte gleiche
Anführungszeichen in f-Strings, PEP 701, z. B. `ui/ink_widget.py:372`). Unter
3.11 bricht schon das Einlesen ab. Die Workflows verwenden 3.12, `setup.sh`
sucht 3.13/3.12 — verlangt wird es aber nirgends ausdrücklich.

## Deckungsgleich — hier ist nichts zu tun

**Designkatalog.** `tools/design_sync.py` ist in beiden Programmen bytegleich
(MD5 `2902093b…`). Alle 26 Profile in `ui/profiles/` sind mit denen in
`views/profiles/` identisch, je 61 Schlüssel. Ein Nutzer, der im LifePlanner
„Gruvbox — Hell" wählt, bekommt in beiden Modulen dieselben Farben.

**Brücke.** Ordnername, Dateinamen und Schemata stimmen auf beiden Seiten
überein (`budgetmanager.import.v1`, `fpm.import.v1`, `fpm.savings-goal.v1` und
die Unterstrich-Altform). `LIFEPLANNER_BRIDGE_DIR` wird beidseitig beachtet,
der Ordner beidseitig auf 0700 gesetzt. `bridge_zustand()` gibt es hier wie
dort (Ausnahme siehe Befund V6).

**Updater.** Alle zehn Module sind bis auf Programmnamen und Docstrings
identisch; `fs_utils.py` unterscheidet sich um eine Leerzeile. Signiertes
Manifest, eingebetteter Vertrauensanker, fail-closed — auf beiden Seiten gleich.

**Sicherheitsbausteine.** `file_permissions` und die Instanzsperre sind inhaltlich
gleich; FPM hat die Sperre sogar sauberer abgelegt (eigenes Modul
`logic/single_instance.py` statt inline in `main.py` wie im BudgetManager).

**Übersetzungen.** FPM 2129 Schlüssel, BudgetManager 2038 — beide vollständig in
de/en/fr, keine Lücke.

**Push-Gates.** Beide haben denselben schlanken Lauf auf main. FPM prüft dort
sogar mehr (Bandit, Import-Smoke, Namens- und DB-Audit); im BudgetManager
laufen dafür `mypy model/` und `lint_procedure_check.py`, die es in FPM nicht
gibt.

## Design — die Abweichungen

### D1. Farben liegen in den Widgets, nicht in einer Rolle

228 Hex-Literale in 16 Dateien, dazu 21-mal `white`/`black` ausgeschrieben:

```
44  ui/pen_widget.py        30  ui/rotation_widget.py     6  ui/statistics_widget.py
41  ui/pen_dialogs.py        9  ui/common.py              5  ui/settings_widget.py
33  ui/dashboard_widget.py   7  ui/rules_widget.py        5  ui/expenses_widget.py
32  ui/ink_widget.py         7  ui/help_widget.py         … 7 weitere mit ≤ 3
```

Im BudgetManager sind es in `views/` **null** — außerhalb von `ui_colors.py`
(dem Rollenspeicher) und dem Theme-Editor. 27 seiner 56 View-Dateien holen ihre
Farben über `ui_colors(self)`, der Rest braucht gar keine.

FPM hat mit `ui/theme.py` das passende Gegenstück bereits gebaut, aber erst 12
von 33 Dateien in `ui/` benutzen es. Die Lücke füllt `ui/host_theme.py`: ein
Affenpatch auf `QWidget.setStyleSheet`, der jedes Stylesheet durch eine
Literal→Rolle-Tabelle schickt. Die Datei nennt sich selbst eine
Übergangslösung. Sie ist es seit v1.0.3.

### D2. 42 Vorkommen fallen durch die Ersetzungstabelle

Von 61 verschiedenen Literalen sind 25 zugeordnet (186 Vorkommen). 36 Literale
(42 Vorkommen) sind es nicht und behalten in jedem Profil ihren hellen Wert.
Ein Teil davon ist Absicht — die acht Kategorienfarben des Diagramms in
`pen_dialogs.py:203` etwa sind Daten, keine Oberfläche. Der Rest sind
Flächenfarben, und dort entsteht der Schaden.

### D3. Belegbar unlesbare Stellen im dunklen Profil

Weil die Ersetzung Vordergrundfarben trifft und die zugehörige Fläche nicht,
kehrt sich der Kontrast um. Ausgeführt gegen `standard_dunkel.json`:

| Stelle | Ergebnis im dunklen Profil | Kontrast |
| --- | --- | --- |
| `ui/help_widget.py:125` Tour-Karte | `#cccccc` auf `#ecf6fd` | **1,47:1** |
| `ui/dashboard_widget.py:105` Kachel-Hover | `#cccccc` auf `#f8fbff` | **1,55:1** |
| `ui/pen_dialogs.py:1227` Warnhinweis | `#f48771` auf `#fde8e8` | **2,09:1** |

WCAG AA verlangt 4,5:1. Die Tour-Karte in der Hilfe ist damit im dunklen Profil
praktisch leer, und die Dashboard-Kachel wird beim Überfahren mit der Maus
unlesbar — also genau in dem Moment, in dem man sie ansieht.

Das ist dieselbe Fehlerklasse, die der Docstring von `ui/theme_manager.py` als
Anlass für den eigenen Designmanager nennt („weisse Karten auf dunklem Grund").
Sie ist verkleinert, aber nicht beseitigt.

### D4. QTreeWidget hat keine Regel

`ui/styles.py` deckt 27 Widget-Klassen ab, aber weder `QTreeWidget` noch
`QTreeView`. `ui/writing_samples_widget.py:103` benutzt einen QTreeWidget als
Mappenbaum. Auswahlfarbe, Hover und Wechselzeilen kommen dort aus der
Systempalette statt aus dem Profil. Der BudgetManager stylt beide Klassen
ausdrücklich (Zeile 82–108 seines Stylesheets), weil sein Kategorien-Tab
denselben Widgettyp benutzt — der Fall ist dort also schon einmal aufgetreten
und behoben worden.

### D5. Kein Design-Editor, keine Schriftgröße in der Oberfläche

Der `ThemeManager` in FPM kann Profile überschreiben und zurücksetzen
(`save_override`, `reset_override`), aber keine Oberfläche ruft das auf. Die
Einstellungen bieten nur Auswahl, „dem Host folgen" und „dem System folgen".
Der BudgetManager hat mit `views/theme_editor_dialog.py` einen Editor mit
Farbwählern je Rolle, Anlegen, Löschen und Zurücksetzen.

Praktische Folge: Alle 26 FPM-Profile tragen `schriftgroesse: 10`, und es gibt
keinen Weg, das zu ändern. Die Schriftgröße läuft in FPM stattdessen über eigene
Stufen (`ui/ui_scale.py`, „Kompakt" bis „Sehr groß"). Zwei Mechanismen für
dieselbe Sache — und der aus dem geteilten Profil ist der, der wirkungslos
bleibt.

### D6. Zwei Affenpatches auf derselben Qt-Methode

`ui/host_theme.py` (Umfärben) und `ui/ui_scale.py` (px-Werte skalieren) ersetzen
beide `QWidget.setStyleSheet`. Sie verketten sich korrekt, weil jeder den
vorgefundenen Aufruf sichert — aber die Reihenfolge hängt daran, wer zuerst
installiert wird, und ein dritter Patch derselben Art wäre schwer zu
durchschauen. Der BudgetManager patcht `setStyleSheet` nicht.

## Verhalten — die Abweichungen

### V1. Keine zentrale Bedienhärtung

Der BudgetManager installiert in `main.py` einen Eventfilter
(`utils/ui_usability.py`). Jedes Fenster, das gezeigt wird, bekommt dadurch
automatisch:

* fehlende `accessibleName`/`accessibleDescription` aus Label und Tooltip,
* einen Screenreader-Hinweis auf Tabellen und Listen,
* **kein Default-Button auf destruktiven Schaltflächen** — „Löschen" lässt sich
  nicht mit Enter auslösen,
* Fokus auf das erste sinnvolle Eingabefeld, ohne vorbelegten Text zu markieren,
* übersetzte Qt-Standardknöpfe in `QDialogButtonBox`.

Die Destruktiv-Erkennung selbst ist Qt-frei in `utils/ui_text_rules.py`
ausgelagert, arbeitet auf Wortgrenzen und deckt de/en/fr ab — damit ein Audit
sie ohne Qt prüfen kann.

FPM hat davon nichts. Es setzt `setDefaultButton` an 19 Stellen von Hand — was
bedeutet: an jeder neuen Stelle wieder, oder eben nicht.

Der Abstand in Zahlen: Barrierefreiheits-Aufrufe 1 (FPM) gegen 25 (BM),
`setStatusTip`/`setWhatsThis` 0 gegen 21, Tooltips 39 gegen 135.

### V2. Jede Rückmeldung ist ein modaler Dialog

172 `QMessageBox`-Aufrufe in FPM, ohne Alternative. Der BudgetManager hat mit
`utils/notifications.py` nicht-modale Hinweise und behält die modale Box für
das, wofür sie gedacht ist: Sicherheitsabfragen, Unwiderrufliches, echte
Fehler. Bei FPM unterbricht auch „Design übernommen" den Arbeitsfluss
(`ui/settings_widget.py:593`).

### V3. Tabellen wachsen nicht mit der Schrift

Der BudgetManager ruft beim Anwenden eines Designs `autosize_all_tables(app)`
und zieht Zeilen- und Kopfhöhen an der neuen Schriftgröße nach. FPM setzt
`setDefaultSectionSize` an genau einer Stelle (`ui/rules_widget.py:448`) und
verlässt sich sonst auf `min-height` in `QTableWidget::item` — was Qt bei
Elementansichten nur eingeschränkt beachtet. Bei Schriftgröße 18–22 werden
Tabellenzeilen deshalb beschnitten.

Das ist derselbe Weg, den FPM bei den Radien schon gegangen ist (Commit
`d633225`, „Radien nach BudgetManager-Vorlage") — nur für die Tabellen noch
nicht.

### V4. Fenstergeometrie wird nicht gemerkt und nicht begrenzt

FPM kennt weder `saveGeometry` noch `restoreGeometry`. Jeder Start beginnt mit
derselben Größe. Der BudgetManager merkt sich die Geometrie und klemmt sie beim
Wiederherstellen mit `clamp_geometry_to_available_screen` in den sichtbaren
Bereich — gegen gespeicherte Geometrien von einem Monitor, den es nicht mehr
gibt.

### V5. DPI-Umgebung wird nicht vorbereitet

Der BudgetManager ruft vor der `QApplication` `configure_qt_scaling_environment()`
und setzt `QT_ENABLE_HIGHDPI_SCALING`, `QT_AUTO_SCREEN_SCALE_FACTOR` und
`QT_SCALE_FACTOR_ROUNDING_POLICY=PassThrough`. FPM setzt in `main.py` nur die
Rundungsrichtlinie über die Qt-API. Auf Windows mit 125/150 % und über RDP ist
das der Unterschied zwischen scharf und unscharf. Der Rest von FPMs
Skalierungsmodul ist gut und richtig kommentiert — es fehlt nur der Vorlauf.

### V6. `bridge_zustand()` zählt anders als das Gegenstück

Beide Programme haben dieselbe Funktion, der BudgetManager nennt FPM im
Docstring ausdrücklich als Gegenstück. Sie verhalten sich aber verschieden,
wenn eine Zeile kaputt ist:

* BudgetManager überspringt die kaputte Zeile und zählt die übrigen.
* FPM benutzt `_iter_jsonl_records`, das bei der ersten ungültigen Zeile eine
  `ValueError` wirft — `bridge_zustand()` fängt sie und meldet **0** für die
  ganze Datei (`logic/budget_export_service.py:445`).

Eine Brücke mit 500 guten und einer kaputten Zeile sieht in FPM aus wie eine
leere Brücke. Genau die Verwechslung, die die Anzeige verhindern sollte.

### V7. Qt-Standardtexte auf zwei verschiedenen Wegen

Der BudgetManager lädt echte Qt-Übersetzungen (`QTranslator`, `utils/qt_translator.py`).
FPM baut in `i18n/qt_i18n.py` eine Rückwärtstabelle aus den eigenen
JSON-Dateien und umhüllt dafür `QDialog.exec`, `QMenu.exec`, die statischen
`QMessageBox`- und `QFileDialog`-Methoden. Das Ergebnis stimmt (das i18n-Audit
ist grün), der Weg ist der aufwendigere und bricht bei jeder neuen Qt-Klasse,
die jemand benutzt.

## Wo FPM vorn liegt

Damit die Richtung stimmt — das ist keine Einbahnstraße:

* **Geführte Tour.** `ui/tour_controller.py` und `ui/tour_overlay.py` gibt es im
  BudgetManager nicht.
* **Instanzsperre als Modul** statt inline in `main.py`.
* **Push-Gates mit mehr Inhalt:** Bandit, Import-Smoke, Namens-Audit,
  DB-Zugriffs-Audit, Windows-Pfadprüfung.
* **Ausnahmen-Ratchet mit Syntaxbaum** statt Textsuche über eine Positivliste —
  laut Changelog war genau diese Positivliste im BudgetManager und im
  LifePlanner der Grund, dass neue Dateien ungeprüft durchgingen. Der bessere
  Stand steht jetzt hier und gehört zurück in die anderen drei Programme.
* **Vollständigere Übersetzung** (2129 gegen 2038 Schlüssel).

Der BudgetManager hat dafür Dinge, die FPM fachlich nicht braucht
(Kontenverschlüsselung, Anmeldung) — die bleiben hier außen vor. Erwähnenswert
ist nur: FPMs Datenbank steht unverschlüsselt auf der Platte und ist allein
durch 0600 geschützt. Für Kaufpreise, Händler und persönliche Notizen ist das
eine bewusste Entscheidung, die man einmal aufschreiben sollte.

## Vorschlag für die Reihenfolge

1. **D3 zuerst** — drei Stellen, drei Zeilen, und die schlimmste sichtbare
   Folge ist weg. Danach ein Test, der jede Rolle-auf-Fläche-Kombination im
   dunklen Profil auf 4,5:1 prüft, damit die vierte Stelle nicht nachwächst.
2. **V6** — eine Zeile. `bridge_zustand()` soll zählen wie sein Gegenstück.
3. **V5** — der DPI-Vorlauf ist eine Funktion, die es im BudgetManager schon
   fertig gibt.
4. **V1** — `ui_usability.py` und `ui_text_rules.py` übernehmen. Das erledigt
   Barrierefreiheit, Enter-auf-Löschen und Fokus in einem Zug für alle
   künftigen Dialoge und macht die 19 Handstellen überflüssig.
5. **D1/D2** — die 42 nicht erfassten Vorkommen auf `ui.theme` umstellen, dann
   die fünf großen Dateien (pen, pen_dialogs, dashboard, ink, rotation).
   Erst wenn dort nichts mehr steht, kann der Affenpatch aus `host_theme.py`
   verschwinden. Ein Audit „kein Hex-Literal außerhalb von theme_manager"
   hält den Stand danach fest — der BudgetManager beweist, dass diese Null
   erreichbar ist.
6. **D4, V3, V4, D5, V7** — je einzeln, ohne Abhängigkeit voneinander.

Die Schritte 1 bis 4 sind klein und übernehmen fertigen Code aus dem
Schwesterprogramm. Schritt 5 ist die eigentliche Arbeit.
