## 1.0.5 – Releasegate: engere Ausnahmen

- Der Releaselauf zu 1.0.4 scheiterte am Ausnahmen-Ratchet: `ui/theme_manager.py`
  fing an drei Stellen `Exception` ab, wo nur zwei Fälle auftreten können.
  `get_session()` wirft `RuntimeError`, solange `init_db()` nicht gelaufen ist,
  und eine noch fehlende Tabelle meldet sich als `SQLAlchemyError`. Genau diese
  beiden werden jetzt gefangen — ein Tippfehler im Zugriff wird nicht mehr
  stillschweigend zum Standardwert.
- `tools/design_sync.py` liest `Iterable` aus `collections.abc`.

## 1.0.4 – Gemeinsamer Designkatalog

### Ein gemeinsamer Designkatalog

LifePlanner, BudgetManager, FountainPen Manager und FreizeitManager liefern
jetzt dieselben **26 Designs** aus — byteweise dieselben Profildateien, erzeugt
und geprüft von `tools/design_sync.py`.

**Warum das nötig war.** Vorher kannten BudgetManager und LifePlanner 26 Designs
mit 29 Rollen, FPM und FreizeitManager sieben mit 38–40. Wer im LifePlanner ein
Design wählte, das ein Modul nicht selbst mitbrachte, bekam dort dessen
Hintergrund, aber Standardblau für Akzent, Karten und Statusfarben — was der
Host nicht mitliefert, fällt im Modul auf das eingebaute Profil zurück. Und drei
Designs trugen in beiden Lagern verschiedene Namen (`Kontrast - Schwarz/Weiß`
gegen `Kontrast Schwarzweiss`, `Hell - Warm (Sepia)` gegen `Warm Sepia - Hell`,
`Dunkel - OLED (Kontrastarm)` gegen `OLED Schwarz`), sodass das Modul das
Hostprofil unter einem Namen suchte, den es selbst nicht führte.

- **55 Rollen je Profil** — ein Kern von 33 für alle Programme plus die
  Bedeutungsfarben der einzelnen. Fehlende Rollen wurden nicht erfunden, sondern
  aus vorhandenen Farben desselben Profils abgeleitet; handverlesene Werte
  blieben unangetastet. Wo zwei Programme dieselbe Rolle unterschiedlich
  führten, gilt der Wert des Hosts.
- **Der Name des Hosts gilt.** Gespeicherte Einstellungen lösen über Aliase
  weiterhin auf.
- **Die Schriftgröße bedeutet überall dasselbe:** 10 heißt normal. Der
  FreizeitManager zeichnet dabei weiterhin 14 Punkt und rechnet den gemeinsamen
  Wert als Faktor darauf um.

### Lesbarkeit ist jetzt Bedingung, nicht Zufall

- **4,5:1 für jede Schrift auf jedem Grund** — die strengste der vier bisherigen
  Schwellen, übernommen aus dem BudgetManager.
- **Die Seitenleiste folgt der Helligkeit des Profils.** Schrift, die auf ihr
  nicht lesbar ist, wird verworfen und neu abgeleitet — in „Solarized – Hell“
  war sie exakt die Farbe der Leiste selbst.
- **Signalfarben heben sich mit mindestens 2,6:1 von der Karte ab.** Ein
  abgeleitetes Gelb erreichte 1,77:1 und war als Ampelfarbe wertlos.
- **Gedimmte Schrift unterscheidet sich messbar von der normalen.** In
  „Solarized – Dunkel“ waren `text` und `text_gedimmt` buchstäblich derselbe Wert.
- **Farbfehlsichtigkeit wird geprüft.** Erfolg/Warnung/Gefahr, die Budget-Typen,
  die vier FPM-Bereiche und die fünf Dringlichkeitsstufen müssen auch bei
  Protanopie, Deuteranopie und Tritanopie unterscheidbar bleiben (Simulation nach
  Viénot/Brettel/Mollon 1999). Vorher waren **348 von 1716 Farbpaaren** nicht
  auseinanderzuhalten, teils sogar identisch — jetzt keines. Repariert wird über
  Helligkeit und Sättigung, nie über den Farbton; der geht dabei gerade verloren.

### Werkzeug

- `tools/design_sync.py check` prüft die eigenen Profile, `build` erzeugt den
  Katalog in allen vier Programmen, `preview` schreibt eine HTML-Übersicht (mit
  den Signalfarben, wie Farbfehlsichtige sie sehen), und `new --name … --akzent …`
  baut aus einer Akzentfarbe ein vollständiges, regelkonformes Design.
- **`build` ist ein Fixpunkt.** Jede Profildatei führt mit, welche Rollen erzeugt
  (`_abgeleitet`) und welche nur nachjustiert wurden (`_vorlage`) — sonst wanderte
  der Katalog mit jedem Lauf ein Stück weiter, statt reproduzierbar zu sein.
- `tests/test_shared_design.py` hält den Katalog zusammen;
  `docs/GEMEINSAMES_DESIGN.md` erklärt Aufbau und Regeln.


### Weiteres
- Die eingebauten Rückfallprofile heißen jetzt wie der Katalog: `Standard - Hell`
  und `Standard - Dunkel`.
- FPMs dunkle Seitenleiste in hellen Designs weicht der gemeinsamen Regel.
- `tools/sync_version.py` zieht jetzt auch README und die drei
  Windows-Anleitungen nach; die Release-Gates lesen die Version aus
  `app_info.APP_VERSION`, statt sie einzutragen.

## LifePlanner compatibility integration

- Added module manifest and LifePlanner bridge-directory support.
- Added signed Windows/Linux .lpmodule release workflow and central-updater guard.

# v0.3.04 – ENTERPRISE RELEASE HARDENING

## Security and data safety
- Central public-network URL policy for image import and online reference lookup.
- Blocks localhost, private/link-local/reserved IPv4 and IPv6, URL credentials and unsafe redirects.
- User cancellation closes active image responses instead of only closing the dialog.
- Atomic, integrity-checked SQLite backups before schema migration and for manual backups.

## Release engineering
- Separate Windows/Linux hash-locked dependency files and fail-closed lock validation.
- Cross-platform gates run before building or publishing.
- Tagged Windows application and installer releases require Authenticode signing and verification.
- GitHub release publication depends on all build/installer gates.

## Operability and verification
- Rotating privacy-filtered production logs, global exception hooks and diagnostics bundle.
- Enterprise updater control-flow suite: 87% coverage across check/apply/startup modules.
- Added security, backup, workflow and cancellation regression tests.

# v0.3.03 – AUDIT-HARDENING

Ergebnis des vollständigen KILLCRITIC-Audits über v0.3.02 (Fehleranalyse, Enterprise, UI, Usability). Drei echte Findings, alle behoben; eine neue Fehlerklasse dauerhaft geschlossen.

## Behobene Findings
- **F-01 (kritisch):** Das dreisprachige `SERVICE_HELP`-Hilfetext-Dict ging beim v0.3.02-Datei-Split verloren (lag exakt im Ersetzungsfenster der `_sync_purchase`-Delegation). Jede Öffnung der Service-Hilfe wäre mit `NameError` gecrasht. Byte-identisch aus v0.3.01 wiederhergestellt, per Guard `service_help_restored` gesichert.
- **F-02 (kritisch):** Vier Importe fehlten in `ui/pen_dialogs.py` (`QInputDialog`, `InkDialog`, `NibDialog`, `RolePrefsDialog`) – darunter der **Override-Begründungs-Prompt** beim Befüllen („Regeln übersteuerbar“, Kernanforderung) sowie die „Neu anlegen“-Flows für Tinte/Feder und die Rollen-Präferenzen. Importe ergänzt und aus `pen_widget` entfernt; Guard `dialog_imports_complete`.
- **F-03 (i18n/Usability):** Der Standard-Override-Grund `'Manuelle Befüllung bewusst bestätigt'` war hartcodiert deutsch und landete so im Override-Log auch unter EN/FR. Neuer Schlüssel `ui.pen_widget.override_reason_default` in allen drei Sprachen (jetzt 2.094 × 3).

## Neue Fehlerklasse geschlossen: Namens-Gate
F-01/F-02 sind `NameError`, die erst beim Öffnen eines Dialogs auftreten – unsichtbar für `compileall` (Syntax) und `tools/import_smoke.py` (nur Modul-Toplevel). Neues Gate **`tools/name_audit.py`**: AST-basiert, meldet **undefinierte Namen als harten Fail** und deckelt **ungenutzte Importe per Ratchet** (Lambda-/Comprehension-/except-Bindungen korrekt, `# noqa` respektiert). In `release-check.yml` verankert, Guard `name_audit_gate`.

## Import-Hygiene: 86 → 0
Das Gate fand 86 ungenutzte Importe (59 Split-Hinterlassenschaften, 27 Altbestand). Alle entfernt – jede Entfernung AST-verifiziert (Name darf nirgends als Lesezugriff vorkommen), abgesichert durch compileall, Import-Smoke, Shim und KILLCRITIC. **Ratchet-Limit: 0.** `test_locale_currency` präzisiert: das Roh-`QDoubleSpinBox()`-Verbot gilt weiter für alle Dateien, die `LocalizedDoubleSpinBox`-Pflicht nur noch für Dateien mit Eingabefeldern (das entlastete `pen_widget` hat keine mehr).

## Verhaltensgleichheit der v0.3.02-Verschiebungen bewiesen
AST-normalisierter Diff aller verschobenen Blöcke gegen v0.3.01: SSRF-Funktion und Redirect-Handler **identisch**; `ServiceHelpDialog`/`ServiceBlockDialog` identisch; `SizeCompareDialog`/`PenDialog`/`LoadInkDialog` weichen **ausschließlich** in den beabsichtigten Query→Repository-Zeilen ab; `sync_purchase_expense_for_pen` nur Docstring/Quoting/Repo-Aufruf/Tag-Konstante. `SERVICE_HELP` byte-identisch.

## Enterprise-/UI-/Usability-Non-Findings (geprüft, in Ordnung)
Kein `eval`/`exec`/`pickle`/`yaml.load`/`os.system`/`shell=True`/`mktemp`/`md5` im Produktionscode (alle Treffer sind Qt-`.exec()`); `subprocess` nur in Listenform (Ordner öffnen, Updater-Relaunch). Migrations-f-Strings speisen sich ausschließlich aus der statischen Literalliste (SEC-002-Design). Dialog-Bilddownload mit vollständiger SSRF-Kette (Pre-Check, geprüfte Redirects, Final-Check, Content-Type, 8-MiB-Limit, Timeout, enge Except-Fänge). `PenRepository.active()` existiert (v0.3.01). Keine sichtbaren deutschen Literale in `pen_dialogs` außerhalb des bewusst dreisprachigen `SERVICE_HELP`. Leerzustände abgedeckt: LoadInk warnt ohne Tinten-Auswahl, SizeCompare zeigt i18n-Hinweis ohne gespeicherte Längen; Override-Prompt bricht bei Abbruch sauber ab.

## Tests/Qualität
- Version 0.3.03, Build `audit-hardening`, alle Pins synchron.
- KILLCRITIC **139** Invarianten (3 neue, per Revert-Simulation diskriminierend) × 1.000 = 139.000 Checks, 0 Findings.
- `name audit: 0/0`, Import-Smoke 63 Module, fünf i18n-Audits grün (2.094 × 3), DB-Ratchet 49/4 Dateien, Exception-Ratchet 146/0.
- Shim: 318 bestanden, 6 bekannte Umgebungs-Fails.

# v0.3.02 – PEN-SPLIT + LOCK-CI

Beseitigt die beiden in v0.3.01 offen benannten Grenzen vollständig: Die Füllerverwaltung ist real zerlegt (nicht mehr exemplarisch), und die Hash-Lock-Datei entsteht per Ein-Klick-CI-Workflow – ohne lokale PyPI-Maschine.

## PenWidget wirklich zerlegt (Audit-P1 abgeschlossen)
- **`ui/pen_widget.py`: 2.739 → 1.295 Zeilen.** Die fünf Dialoge (PenDialog, LoadInkDialog, ServiceBlockDialog, ServiceHelpDialog, SizeCompareDialog) leben jetzt in **`ui/pen_dialogs.py`** (1.413 Z.), gemeinsame Label-/Optionshelfer in **`ui/pen_common.py`**. `ui/pen_widget` re-exportiert alle Klassen – bestehende Importe (`from ui.pen_widget import PenDialog`) bleiben gültig.
- **Alle 20 direkten UI-Queries eliminiert** (17 Pen, 3 Ink): neue Repository-Methoden (Nib, NibFormat, PenNibSetup, WritingSample, Expense.for_pen/Auto-Kauf, Ink.usable_sorted/find_variant, Pen.find_variant) plus **`logic/pen_service.py`** mit der fachlichen Logik (Varianten-/Dublettensuche, Einzel-Aktiv-Auswahl, NibFormat-Wiederverwendung/-Anlage, Ähnliche-Feder-Erkennung, Kaufpreis-Spiegelung in den Ausgaben-Tracker).
- **SSRF-Bildschutz (SEC-001) nach `logic/image_url_security.py`** verschoben – Qt-frei und damit direkt verhaltenstestbar; die Security-Tests laufen jetzt auch in der Sandbox.
- **DB-Ratchet verschärft:** Obergrenze 69 → **49**; `pen_widget.py`, `pen_dialogs.py` und `ink_widget.py` sind zusätzlich zu `dashboard_widget.py` **dauerhaft query-frei** verankert.

## Neues Release-Gate: Import-Smoke
- **`tools/import_smoke.py`** importiert alle 63 Produktionsmodule real (in der Sandbox mit bedingten Stubs aus `tests/_stub_env.py`, in der CI gegen echte Pakete) und ist in `release-check.yml` verankert.
- Anlass war ein in v0.3.01 eingeschleppter, von `compileall` unsichtbarer Importfehler in `ui/pen_widget.py` (`PenRepository, _data_dir` aus dem falschen Modul) – **in dieser Version behoben**; das neue Gate hätte ihn sofort gemeldet und fängt künftig jede solche Regression.

## Hash-Lock ohne lokale Maschine
- Neuer Workflow **`.github/workflows/generate-lockfile.yml`** (manuell startbar): erzeugt `constraints.lock` mit sha256-Hashes auf einem GitHub-Runner, validiert per `--check`, lädt die Datei als Artefakt hoch und **öffnet automatisch einen Pull Request**. Nach dem Merge installiert der Windows-Release strikt mit `--require-hashes`.

## GUI-Smoke deckt die neuen Pfade ab
- `tools/gui_smoke_test.py` legt jetzt Minimaldaten an (Tinte, befüllter Füller mit 45-Tage-Ladung, gesperrter Füller), erzwingt einen Dashboard-Refresh mit gefüllten Timer-/Service-Tabellen und **konstruiert alle fünf ausgelagerten Dialoge** – Split- und Importfehler fallen damit im CI-Offscreen-Lauf auf, nicht erst am Desktop.

## Tests/Qualität
- Neue Verhaltenstests `tests/test_pen_services_0302.py` (11 Fälle) für Service und neue Repositories.
- Version 0.3.02, Build `pen-split-lock-ci`, alle Pins synchron.
- KILLCRITIC **136** Invarianten (7 neue, alle per Revert-Simulation diskriminierend) × 1.000 = 136.000 Checks, 0 Findings.
- Fünf i18n-Audits grün (2.093 × 3). Sandbox-Shim: **318 bestanden, 6 bekannte Umgebungs-Fails** (5× PySide6-GUI, 1× echtes SQLAlchemy) – einer weniger als zuvor, weil die SSRF-Tests jetzt Qt-frei laufen.

# v0.3.01 – ENTERPRISE FOLLOW-UP

Setzt die fünf offenen (nicht releaseblockierenden) Punkte des v0.3.00-Enterprise-Audits um. Alle v0.3.00-Härtungen (ResponsiveDialog, DB-Lifecycle, SSRF-Bildimport, statische Migration, Onboarding-Rerun, Release-Gates) bleiben erhalten.

## Architektur (Audit-P1)
- **Dashboard-Refresh zerlegt**: Die 309-Zeilen-Methode `DashboardWidget.refresh()` ist in den neuen, Qt-freien `logic/dashboard_service.py` (Datenbeschaffung, Klassifikation, Schwellwerte, Texte) plus fünf schlanke Renderer aufgeteilt. Das Widget schrumpft von 878 auf 731 Zeilen und enthält **null** direkte `session.query`-Aufrufe mehr.
- **Repository-Schicht** (`database/repositories.py`): Pen/Ink/Paper/Expense/InkLoad-Repositories bündeln Abfragen. Dashboard nutzt sie vollständig; Pen- und Ink-Haupttabellen laufen über `all_sorted()`/`active_sorted()`.

## Verhaltenstests (Audit-P1 Coverage)
Vier neue Suites gegen die kritischen Fehlerpfade, in der CI gegen echtes SQLAlchemy, in der Sandbox über einen bedingten conftest-Stub:
- `test_updater_behavior_0301.py` – Manifest-Parsing, SemVer (0.2.9 < 0.2.10, garbage→konservativ False), ZipSlip-Abwehr, Staging-Versionswahl, Exclude-Semantik, Ergebnis-Persistenz.
- `test_rule_engine_behavior_0301.py` – alle sechs Bedingungstypen, Warnstufen-Malus vs. `score_delta`, Blocking-Verdrängung, Boni, Score-Clamp, `max_days_for`-Kaskade.
- `test_rotation_engine_behavior_0301.py` – Standzeit-Bonuskurve, Farbfamilien-Penalty (Fixpaar-Ausnahme), Randomness-Sicherheitsfilter (harte Blocker raus, 💍 bleibt; 0 %/100 %-Mischung; keine Input-Mutation).
- `test_dashboard_service_0301.py` – Wertberechnung, Timer-Klassifikation, Service-Sortierung, All-Clear, Repository-Delegation.

## Fehlerbehandlung (Audit-P2)
- Neues zentrales `logic/log_utils.log_unexpected(context, exc)`.
- Acht breite Handler präzisiert (Updater-JSON/IO → `OSError`/`JSONDecodeError`/`UnicodeDecodeError`; Tour-Import-Guards → `ImportError`; Budget-Datumsparser → `ValueError`/`TypeError`).
- **Ratchet-Gate** `tools/exception_audit.py`: verbietet nackte `except:` (0) und deckelt breite Handler bei 146 (nur senkbar).

## Supply-Chain (Audit-P2)
- `tools/gen_lockfile.py`: erzeugt `constraints.lock` mit sha256-Hashes aller Abhängigkeiten (`--check`-Modus als Release-Gate). Der Windows-Release installiert bei vorhandener Lock-Datei strikt mit `--require-hashes`.

## DB-Zugriff-Ratchet (Audit-P1)
- `tools/db_access_audit.py`: hält `dashboard_widget.py` dauerhaft query-frei und deckelt direkte UI-Queries bei 69 (nur senkbar).

## CI
- `release-check.yml`: neuer Schritt „Verify dependency lock and hardening ratchets" (Lock-Check + beide Ratchets).
- `windows-release.yml`: Hash-Installation bei vorhandener Lock-Datei, sonst Fallback.

## Tests/Qualität
- Version 0.3.01, Build `enterprise-followup`, alle Pins synchron.
- KILLCRITIC 129 Invarianten (13 neu, alle per Revert-Simulation als diskriminierend bewiesen) × 1.000 = 129.000 Checks, 0 Findings.
- Fünf i18n-Audits grün (2.093 × 3). Sandbox-Shim: 305 bestanden, 7 bekannte Umgebungs-Fails.

## Ehrliche Grenzen
- Große Klassen (P1) und breite Handler (P2) werden über **Ratchets schrittweise** abgebaut, nicht in einem Big-Bang. `PenWidget` ist exemplarisch entlastet (Haupttabelle über Repository), aber noch nicht zerlegt.
- Der Hash-Lock wird auf einer Maschine **mit PyPI-Zugang** erzeugt (`python tools/gen_lockfile.py`); die Prüf-Sandbox kann das nicht. Bis dahin läuft der Check bewusst im Entwicklungsmodus (Exit 0).

# v0.3.00 – ONBOARDING ENTERPRISE MERGED

## Neu
- Der vierstufige Einrichtungsassistent kann unter Einstellungen jederzeit erneut gestartet werden.
- „Onboarding zurücksetzen“ erzwingt die Tour beim nächsten Start auch bei vorhandenen Füllern, Tinten oder Federn.
- Tour- und Wizard-Abschluss räumen das Force-Flag zuverlässig auf.

## Enterprise-Merge und Fehlerbehebung
- v0.2.99 wurde nicht als Releasebasis übernommen, da sie mehrere v0.2.98-Härtungen zurücknahm.
- Zentraler `ResponsiveDialog`, schmale Einstellungen, sichtbare Dashboard-Kachelaktion und verzögerter Dashboard-Reflow bleiben erhalten.
- Sauberer SQLAlchemy-/SQLite-Lifecycle, Ruff-, Coverage- und Build-Abhängigkeiten bleiben erhalten.
- Entfernte v0.2.98-Regressionstests und Auditberichte bleiben Bestandteil des Quellstands.

## Sicherheit und Releaseprozess
- Bildimporte per URL blockieren lokale, private, reservierte und nicht global routbare Ziele.
- Redirects, finale URL, MIME-Typ und Größenlimit werden geprüft.
- Legacy-Migrations-SQL verwendet nur feste Anweisungen.
- Bandit prüft mittlere und hohe Sicherheitsfindings als Release-Gate.

---

# v0.2.98 – ENTERPRISE RESPONSIVE UI HARDENING

## Behoben
- Große Dialoge werden gegen die verfügbare Bildschirmfläche begrenzt und bei Bedarf scrollbar.
- Die Einstellungen wechseln auf sehr schmalen Fenstern in eine kompakte Auswahl und ordnen Aktionsbuttons responsiv an.
- Graue Sekundärtexte wurden auf eine zentral kontrastreichere Farbe angehoben.
- Dashboard-Kacheln besitzen nun zusätzlich zum Doppelklick die sichtbare Aktion **„Im Reiter öffnen“**.
- Datenbank-Sessions und Engine-Verbindungen werden vor Reinitialisierung sowie beim Programmende geschlossen.
- SQLite-Verbindungen der Datenbankwartung werden auch bei Fehlern zuverlässig freigegeben.

## Qualität
- Zentrale `ResponsiveDialog`-Basis statt vieler isolierter Größenfixes.
- Neue Verhaltenstests für Dialoggrenzen, Einstellungen, Button-Reflow, Dashboard-Navigation und Kontrast.
- Kritische Ruff-Prüfungen und eine Coverage-Untergrenze von 50 % in die CI aufgenommen.
- Dashboard-i18n und initialer Viewport-Reflow durch visuelle Regressionstests gehärtet.
- Wiki und Handbücher in Deutsch, Englisch und Französisch auf die neue Bedienung aktualisiert.

## Erhalten
- Mehrsprachiges Hilfe-Wiki und vollständige Handbücher aus v0.2.97.
- Fokus-Kachel-Dashboard aus v0.2.96.
- Formular-Datenerhalt aus v0.2.95.
- Responsive Laptop-/Fensterskalierung und Locale-/Währungs-Härtung aus v0.2.92–v0.2.94.

---

# v0.2.97 – MEHRSPRACHIGES HILFE-WIKI & DOKUMENTATION

## Neu
- Durchsuchbares In-App-Wiki mit Mehrwortsuche und klarer Trefferanzeige.
- Kontextbezogener Toolbar-Button öffnet direkt das passende Hilfekapitel.
- Handbuch-Button öffnet automatisch Deutsch, Englisch oder Französisch.
- Vollständige Handbücher `BENUTZERHANDBUCH_DE.md`, `USER_MANUAL_EN.md` und `MANUEL_UTILISATEUR_FR.md`.
- Eigenes Wiki-Kapitel für sichere Dateneingabe, Maße, Einheiten und Medien.

## Behoben
- Veraltete Einfachmodus-Beschreibung korrigiert.
- Technische `legacy_exact`-Hilfeschlüssel durch sprechende Schlüssel ersetzt.
- Dokumentationsstand auf v0.2.97 synchronisiert.
- Füller-Dialog warnt vor dem Verwerfen geänderter, ungespeicherter Eingaben.

## Erhalten
- Fokus-Kachel-Dashboard aus v0.2.96.
- Formular-Datenerhalt aus v0.2.95.
- Responsive Laptop-/Fensterskalierung aus v0.2.93/v0.2.94.
- Locale-/Währungs-Härtung aus v0.2.92.

---

# v0.2.96 – FOKUS-KACHEL-DASHBOARD

## Neu
- Dashboard auf fünf kompakte Informationskacheln umgestellt.
- Wichtigste Kennzahlen werden direkt als Text dargestellt.
- Einfachklick fokussiert und erweitert exklusiv die zugehörige Tabelle.
- Erneuter Klick klappt die Tabelle wieder ein; ein Klick auf eine andere Kachel wechselt die Detailansicht.
- Doppelklick auf Kachel oder Tabellenzeile öffnet den passenden Reiter.
- Responsiver Kachelumbruch mit 3/2/1 Spalten.

## Erhalten
- Laptop- und DPI-Skalierung aus v0.2.93/v0.2.94.
- Locale-/Währungs-Härtung und Formular-Datenerhalt aus v0.2.95.

---

# v0.2.95 – FÜLLER-FORMULAR DATENERHALT

## Behoben
- Numerische Füllerdaten mit sichtbaren Einheiten (`mm`, `g`, `ml`) bleiben nach Fokus- und Tabwechsel erhalten.
- Geldfelder mit Währungspräfix oder -suffix werden ebenfalls korrekt geparst.
- Ungültige Zwischenstände setzen einen bereits bestätigten Wert nicht mehr still auf `0`.

## Ursache
Qt übergab den sichtbaren SpinBox-Text inklusive Präfix/Suffix an den zentralen Locale-Parser. Texte wie `143,00 mm` waren dadurch keine gültige Zahl und wurden beim Verlassen des Feldes zu `0`.

## Absicherung
- Neuer Regressionstest `tests/test_pen_numeric_input_persistence_0295.py`.
- Reale Offscreen-Laufzeitprüfung des kompletten Füllerdialogs über alle Tabs.

---

# v0.2.94 – LOCALE & CURRENCY HARDENING

Behebt den gemeldeten Fehler `39,96 CHF` statt `CHF 39.96` bei deutscher OS-Locale und die zugrundeliegende verteilte Locale-Architektur.

## Root-Cause
Zwei Ursachen: (1) `QDoubleSpinBox` übernahm Komma/Punkt von der Betriebssystem-Locale statt von der App-Region. (2) Der alte `parse_number` entfernte bei Dezimal=Punkt alle Kommata – `39,96` wurde zu `3996` (Faktor-100).

## Fixes
- **Robuster Parser** (`i18n/translator.parse_number`): Dezimalzeichen am letzten Punkt/Komma erkannt; Apostroph, Leerzeichen und das jeweils andere Zeichen als Gruppierung; konsistente Dreiergruppierung erzwungen; mehrdeutige Eingaben (`12,34,56`) abgelehnt; Währungssymbole/-codes und schmale Leerzeichen entfernt.
- **Zentrale Eingabe** `ui/localized_inputs.py`: `LocalizedDoubleSpinBox` (App-Locale statt OS via `QLocale.C` + eigener Validator/Parser) und `MoneySpinBox` (ISO-Code als Präfix/Suffix je Region, `set_currency`/`refresh_locale`). Alle rohen `QDoubleSpinBox()` in pen/ink/paper/expenses/wishlist/writing_samples/enthusiast_lab ersetzt.
- **CSV-Import** (pen, ink) und **Wechselkurse** (settings) nutzen den gemeinsamen Parser; Kurse nur positiv/endlich.
- **ISO-Währungscodes** bleiben hartcodiert (CHF/EUR/USD/GBP), nicht übersetzbar.

## Festgelegtes Verhalten
Sowohl `39,96` als auch `39.96` werden als **39.96** gespeichert. Die DB bleibt sprachneutral; die Region wirkt nur auf Ein-/Ausgabe. Anzeige: CH `CHF 1'234.56`, DE/AT `1.234,56 EUR`, FR `1 234,56 EUR`, UK `GBP 1,234.56`, US `USD 1,234.56`.

## Absicherung
- `tests/test_locale_currency_0292.py`: realer Parser-Test über alle Regionen (Punkt/Komma-Eingabe → gleicher Wert, Gruppierung, mehrdeutige Ablehnung, Vorzeichen, Symbol-Strip) plus statische Verdrahtungs-Guards.
- 5 neue KILLCRITIC-Invarianten (zentrale SpinBox existiert, kein rohes QDoubleSpinBox mehr, CSV nutzt Parser, ISO-Codes fix).

## Ehrliche Einschränkung
Historische Daten aus fehlerhaften EN/FR-Builds (CHF als USD/EUR gespeichert) lassen sich nicht sicher automatisch korrigieren, da echte Fremdwährungskäufe nicht unterscheidbar sind. Empfehlung: Alt-Datensätze einmal in Füller-, Tinten-, Papier-, Wishlist- und Ausgabenansicht sichten. Kein GUI-Smoke-Test in der Sandbox möglich.

---

# Changelog

## 1.0.1 – 20. August 2026

### Zentrale Darstellung im LifePlanner
- FPM folgt im LifePlanner dem dort zentral gewählten Designprofil: Hauptfenster, Seitenleiste, Toolbar, Tabellen, Eingabefelder, Karten und Dialoge übernehmen dessen Farben.
- Die Schriftgröße des Profils wirkt als Skalierungsfaktor auf das bestehende UI-Scaling. Der Standardwert 10 ergibt exakt das bisherige Schriftbild.
- Neu: `ui/host_theme.py` liest das Profil aus `LIFEPLANNER_THEME_FILE` (Format `lifeplanner.theme.v1`). `PALETTE_ROLES` ordnet dabei jedem Farbliteral des Stylesheets die Rolle zu, die es tatsächlich hat.
- **Ohne LifePlanner ändert sich nichts.** Ist die Variable leer, liefert `get_stylesheet()` unverändert die bisherigen Farben; ein Regressionstest sichert das ab.
- Nicht enthalten: Inline-`setStyleSheet`-Aufrufe einzelner Widgets führen weiterhin eigene Farben. Sie folgen dem Profil noch nicht.

## v0.2.91 — Cross-Platform Release Hardening

- Gemeinsamer GitHub-Release für Windows und Linux.
- Windows- und Linux-PyInstaller-onedir-Builds aus demselben Tag.
- Portables Windows-ZIP und portables Linux-ZIP mit lokalem `data/`-Ordner.
- Separater Windows-Installer und Installer-ZIP.
- Gemeinsames `latest.json` für Updater auf Windows und Linux.
- Gemeinsame SHA256-Prüfsummen.
- Dauerhafter Guard gegen Windows-ungültige Git-Dateipfade.
- Deutsche Anleitung aktualisiert und Release-Dokumentation konsolidiert.
- Historische Einzelberichte nach `docs/history/` verschoben.

## Historie

Die ausführlichen Berichte früherer Versionen befinden sich in `docs/history/`.

## v0.2.91 – Release-Readiness-Härtung

- KILLCRITIC führt jetzt tatsächlich 1000 deterministische Schleifen aus.
- Dateizugriffe im KILLCRITIC-Audit werden gecacht, damit 86.000 Prüfungen schnell bleiben.
- Ungültige Loop-Werte werden kontrolliert abgewiesen.
- Windows-Pfadprüfung beschneidet Build-, Dist- und Cache-Verzeichnisse bereits beim Traversieren.
- Laufzeittests für Windows-/Linux-Release-Assets, SHA256-Manifest und Linux-Ausführungsrechte ergänzt.
- Release-Validierung auf den tatsächlich geprüften Stand aktualisiert.

## v0.2.94 – Laptop-Dashboard
- Dashboard vollständig scrollbar gemacht.
- KPI-Karten und Schnellaktionen reagieren auf die Fensterbreite (4/2/1 Spalten).
- Karten kompakter gestaltet und Tabellen für kleine Fenster gehärtet.
- Inhalte bleiben bei 1366×768 und kleineren Fenstern erreichbar.
