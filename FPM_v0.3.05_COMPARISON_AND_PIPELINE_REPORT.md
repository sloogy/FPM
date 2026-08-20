# FPM – Vergleich v0.3.04 Enterprise Hardened vs. LifePlanner Fixed und Ergebnis v0.3.05

## Kurzurteil

Die **Enterprise-Hardened-Version** ist die stärkere Basis für Qualität, Security und Release-Gates. Die **LifePlanner-Fixed-Version** ergänzt die notwendige LifePlanner-Kompatibilität, bindet sie aber als separate Release-Pipeline an und umgeht damit Teile der vorhandenen Enterprise-Release-Kette.

Die neue **v0.3.05** übernimmt deshalb die Enterprise-Version als Release-Fundament und integriert die sinnvollen LifePlanner-Erweiterungen direkt in diese Pipeline.

## Unterschiede der beiden gelieferten v0.3.04-Versionen

### Nur in `FPM_v0.3.04_LIFEPLANNER_FIXED_2026-08-02`

- `module.json`
- `tools/build_lifeplanner_module.py`
- `.github/workflows/lifeplanner-module-release.yml`
- `tests/test_lifeplanner_host_contract.py`
- `tests/test_lifeplanner_module_release.py`
- `SOURCE_TREE_SHA256_v0_3_04_COMPATIBILITY_FIXED.txt`

Zusätzlich geändert:

- `logic/budget_export_service.py`: LifePlanner-Bridge-Verzeichnis per `LIFEPLANNER_BRIDGE_DIR` möglich.
- `ui/settings_widget.py`: interner Updater wird bei `LIFEPLANNER_CENTRAL_UPDATER=1` blockiert.
- DE/EN/FR erhalten den neuen LifePlanner-Updater-Hinweis.

Die großen Textdifferenzen in den drei i18n-Dateien bestehen überwiegend aus JSON-Umsortierung. Semantisch wurde je Sprache nur der neue LifePlanner-Hinweis ergänzt.

## Findings in der LifePlanner-Fixed-Version

1. **Separater Releasepfad**
   `lifeplanner-module-release.yml` veröffentlicht unabhängig vom Enterprise-Workflow. Dadurch existieren zwei Publisher für denselben GitHub-Release.

2. **Hartcodierte Version**
   Workflow-Trigger und Modul-Assetnamen enthalten `v0.3.04` bzw. `0.3.04` direkt.

3. **Enterprise-Gates werden umgangen**
   Der LifePlanner-Workflow baut FPM nochmals separat mit PyInstaller und führt nur zwei sehr kleine Contract-Tests aus. Er konsumiert nicht das bereits vollständig geprüfte Enterprise-Build-Artefakt.

4. **Keine Herkunftsbindung des Runtime-Artefakts**
   Das Modul selbst signiert `component.json`, aber der zugrunde liegende Runtime-Build wird vor dem Modulbau nicht kryptografisch attestiert und erneut verifiziert.

5. **Doppeltes Release-Rennen**
   Beide Matrix-Jobs des separaten Modulworkflows können `gh release create` / `gh release upload` ausführen, während auch der Enterprise-Workflow veröffentlicht.

6. **i18n-Laufzeitfehler**
   Der neue Schlüssel wurde als Root-Key `"settings.lifeplanner_central_updater"` gespeichert. Der Translator löst Punktnotation aber hierarchisch auf und erwartet `settings -> lifeplanner_central_updater`. Die UI konnte deshalb den Keynamen statt der Übersetzung anzeigen.

7. **Tests zu oberflächlich**
   Es gab keinen echten Modulbau mit Schlüsselmaterial, keine Signaturprüfung, keinen Manipulationstest und keine Host-Installation des fertigen `.lpmodule`.

## Umsetzung in v0.3.05

### 1. Version auf v0.3.05

- `APP_VERSION = "0.3.05"`
- Release-Datum: 20. August 2026
- Build-ID: `enterprise-lifeplanner-pipeline`
- Installer, `version.json`, `VERSION_INFO.txt`, Updater-Templates und `module.json` synchronisiert.

### 2. Übersetzungsschlüssel korrekt verschachtelt

In DE, EN und FR liegt der Schlüssel nun wirklich unter:

`settings -> lifeplanner_central_updater`

Ein Regressionstest prüft zusätzlich die echte Laufzeitauflösung über `Translator.t()`.

### 3. LifePlanner-Modulbau in Enterprise-Pipeline integriert

Die separate Datei `.github/workflows/lifeplanner-module-release.yml` wurde entfernt.

Der zentrale Release-Workflow ist jetzt die einzige Release-Kette:

`Enterprise Gates -> Native Builds -> Windows Signing -> Installer -> Runtime Attestation -> Module Build -> Host Verify/Install -> Final Assets -> Publish`

### 4. Module nur aus geprüften und signierten Build-Artefakten

Neu:

- `tools/runtime_artifact.py`
- `tools/release_signing.py`

Nach allen Enterprise-Gates wird für jedes Runtime-Bundle ein deterministischer Tree-Hash erzeugt und mit Ed25519 signiert. Der Modul-Builder akzeptiert das Runtime-Verzeichnis nur, wenn:

- Signatur gültig ist,
- App-Version stimmt,
- Plattform stimmt,
- Signing-Key-ID stimmt,
- Tree-Hash exakt dem aktuellen Runtime-Inhalt entspricht.

Eine Änderung nach der Signatur führt fail-closed zum Abbruch.

### 5. Genau ein Publishjob

Im gesamten Workflow verbleibt genau ein `gh release create`.

LifePlanner-Module werden nur als Build-Ergebnis erzeugt und anschließend gemeinsam mit Standalone-ZIPs und Installer vom zentralen Publishjob veröffentlicht.

### 6. Automatische Synchronisierung von Version, Tag, Manifest und Assetnamen

Neu:

- `tools/release_metadata.py`
- `sync_version.py` synchronisiert jetzt zusätzlich `module.json`.

Aus `APP_VERSION` werden automatisch abgeleitet:

- Git-Tag `v<version>`
- Windows-/Linux-Portable-ZIP-Namen
- Installer-Namen
- Windows-/Linux-LifePlanner-Modulnamen
- `latest.json`-URLs und Modul-Assets

Der Release-Workflow enthält keine hartcodierte `v0.3.05`.

### 7. Echte Modul-/Signatur-/Manipulations-/Hosttests

Neu ist eine vollständige Testkette mit temporären Ed25519-Schlüsseln:

- echter Windows-Modulbau
- echter Linux-Modulbau
- Prüfung der `component.json`-Signatur
- Prüfung der Runtime-Attestation
- Ablehnung einer nachträglich veränderten Runtime
- Ablehnung manipulierter `component.json`
- Ablehnung manipulierter Payload-Dateien
- Ablehnung von ZIP-Path-Traversal / Windows-Pfadtricks
- echte Testinstallation in eine LifePlanner-artige Versionsstruktur
- Prüfung der erwarteten Windows-/Linux-Executables

Zusätzlich führt der reale Releasejob vor dem Publish eine Host-Verifikation und Testinstallation beider tatsächlich gebauten `.lpmodule` durch.

## Sicherheitsverbesserung des Secret-Handlings

`LIFEPLANNER_UPDATE_PRIVATE_KEY_B64` wird **nicht** jobweit gesetzt. Das Secret ist nur in den Schritten sichtbar, die es benötigen:

- Key-Gate
- Runtime-Attestation
- Modul-Signierung

Checkout-, Setup- und Download-Actions erhalten den privaten Schlüssel nicht.

## Lokale Verifikation

Bestanden:

- 418 Tests mit realem PySide6; 75,37 % Kern-Coverage
- Linux-PyInstaller-Onedir erfolgreich gebaut und initialisiert
- 14 gezielte Release-/LifePlanner-Tests
- 5/5 i18n-Audits
- 139.000 KILLCRITIC-Prüfungen, 0 Findings
- Compileall
- Windows-Pfad-Audit
- Import-Smoke: 66 Produktionsmodule
- Name-Audit
- Exception-Audit
- DB-Access-Audit
- YAML-Parsing aller Workflows

Zusätzlich lokal bestanden:

- vollständige PySide6-GUI-Suite und GUI-Smoke
- Ruff
- Bandit
- Linux-/Windows-Lockprüfung und Binary-only-Installationsplan

Extern verpflichtend bleibt die reale Windows-Authenticode-Signierung sowie die Reproduktion in der offiziellen GitHub-Matrix.

## Noch bestehendes absichtliches Release-Gate

`constraints-linux.lock` und `constraints-windows.lock` wurden mit dem Generator erzeugt, vollständig hashvalidiert und per plattformspezifischem Binary-only-Installationsplan geprüft. Die Linux-Lockdatei wurde zusätzlich in eine saubere Python-3.12-Umgebung installiert und für alle lokalen Gates verwendet.

Das öffentliche Binary-Release bleibt bis zur grünen GitHub-Matrix und realen Signierung fail-closed.

## Ergebnis

**v0.3.05 ist die vollständigere und architektonisch richtige Zusammenführung der beiden v0.3.04-Stände.**

Die LifePlanner-Kompatibilität ist erhalten, aber sie besitzt keinen eigenen schwächeren Releasepfad mehr. Standalone-App und LifePlanner-Modul stammen aus derselben geprüften Buildkette und werden gemeinsam veröffentlicht.
