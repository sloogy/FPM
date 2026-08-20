# FountainPen Manager v0.3.05 – Enterprise Release Hardening Report

## Ergebnis

Die im v0.3.03-Enterprise-Audit bestätigten Quellcode- und Pipelinefehler wurden in v0.3.05 behoben. Der Stand ist als **lokal vollständig validierter Enterprise-Release-Candidate** freigabefähig. Beide Plattform-Locks sind erzeugt und geprüft. Ein öffentliches Binärrelease bleibt absichtlich gesperrt, bis die vollständige Windows-/Linux-Matrix grün ausgeführt und die Windows-Artefakte mit dem realen Authenticode-Zertifikat signiert wurden.

## Behobene Findings

| ID | Auditfinding | Umsetzung v0.3.05 | Verifikation |
|---|---|---|---|
| EC-01 | PowerShell-Syntax im gemeinsamen Linux/Windows-Job | Plattformneutraler Bash-/Python-Aufruf; Windows-spezifische Schritte ausschließlich `pwsh` | YAML-Parsing und statische Workflowtests |
| EC-02 | Aktiver Bildimport ohne SSRF-Schutz | Zentrale Public-Network-Policy im tatsächlich genutzten Downloadpfad | Localhost/RFC1918/link-local/IPv6/Redirect-/DNS-Rebinding-Tests |
| EC-03 | Veröffentlichung nicht vollständig gegated | Releasejob benötigt Build- und Installerjob; Production-Environment; Publish erst nach Artefaktprüfung | Workflow-Regressionsprüfung |
| EC-04 | Fehlendes bzw. nicht hartes Dependency-Lock | Separate Linux-/Windows-Locks; fehlende Locks ergeben Exitcode 1; nur Hash-/Binary-Installation | Lock-Tool- und Workflowtests |
| EC-05 | Kritische Updaterpfade untertestet | Neue Kontrollflusstests für Check, Apply und Startup | 87 % kombinierte Coverage; 94/82/97 % je Modul |
| EC-06 | Keine Produktionsdiagnostik | Rotierende, datenschutzgefilterte Logs, globale Exception-Hooks, Qt-Logging und Supportbundle ohne DB/Medien | Bundle-/Import-/Namensaudit |
| EC-07 | Unsigned Windows Release | Tag-Releases verlangen Zertifikats-Secrets; EXE und Installer werden signiert und mit `signtool verify` geprüft | Statische Pipelineprüfung; echtes Zertifikat extern erforderlich |
| EC-08 | Unsichere DB-Kopie vor Migration | SQLite-Backup-API, WAL-Checkpoint, `.partial`, Integrity-Check und atomarer Replace; Migration stoppt bei Backupfehler | Restore-/Integritäts-/Fehlerpfadtests |
| EC-09 | Abbrechen stoppte Netzwerk nicht | Abbruchsignal schließt die aktive Response und beendet den Worker kontrolliert | Blocking-Response-Regressionstest |
| EC-10 | Zweiter Recherchepfad ohne Netzschutz | Referenzsuche und Updater-Manifest/Asset-Download verwenden dieselbe Public-Network-Policy; die tatsächliche TCP-Gegenstelle wird nach dem Verbindungsaufbau erneut geprüft | SSRF-Regressionstests |
| EC-11 | Breite Fehlerbehandlung/Schuld | Broad-Exception-Ratchet von 146 auf 145 reduziert; 0 nackte `except` | `exception_audit.py` |
| EC-12 | Alter Bericht überschätzte SSRF-Schutz | Releaseberichte vollständig korrigiert | Dokumentationsprüfung |

| LP-01 | Separate LifePlanner-Release-Pipeline konnte parallel veröffentlichen | Modulbau in zentralen Enterprise-Workflow verschoben; nur ein `gh release create` verbleibt | Workflow-Regressionstest |
| LP-02 | Modulworkflow baute Runtime erneut statt geprüfte Artefakte zu verwenden | Module konsumieren ausschließlich zuvor gegatete Runtime-Artefakte | End-to-End-Modulbautest |
| LP-03 | Keine kryptografische Herkunftsbindung der Runtime vor Modulbau | Ed25519-Attestation mit deterministischem Tree-Hash; Builder verifiziert fail-closed | Signatur- und Tamper-Tests |
| LP-04 | Tag/Manifest/Assetnamen hartcodiert | `app_info.py` bleibt Versionsquelle; `sync_version.py` synchronisiert `module.json`; `release_metadata.py` leitet Tag und Namen ab | Versions-/Workflowtests |
| LP-05 | LifePlanner-Update-Hinweis in i18n flach statt verschachtelt | `settings.lifeplanner_central_updater` in DE/EN/FR korrekt unter `settings` verschachtelt | Translator-Regressionstest + 5 i18n-Audits |
| LP-06 | Kein echter Host-Installationsnachweis | Referenz-Host-Contract verifiziert Signatur, Pfade, Payload-Hash, Manifest und installiert atomar | Windows-/Linux-Host-Installationstest |

## Lokale Beweise

- 418 Tests in der exakten Linux-Lockumgebung bestanden; Kern-Coverage 75,37 %.
- Linux-PyInstaller-Onedir erfolgreich gebaut und als isoliertes Bundle initialisiert.
- 66 Produktionsmodule im Import-Smoke mit realem SQLAlchemy und PySide6 importierbar.
- Updater-Kontrollpfade: 86,55 % Coverage, Gate 85 % bestanden.
- 139.000 KILLCRITIC-Prüfungen, 0 Findings.
- 2.109 i18n-Schlüssel in DE/EN/FR; alle fünf i18n-Audits bestanden.
- 0 undefinierte Namen, 0 ungenutzte Importe.
- 145 breite Exception-Handler innerhalb des Ratchets, 0 nackte `except`.
- Versions-, Pfad-, Datenbankzugriffs- und Compile-Gates bestanden.

## Noch extern auszuführen

1. Repository-Secrets `WINDOWS_SIGNING_CERT_BASE64`, `WINDOWS_SIGNING_CERT_PASSWORD` und `LIFEPLANNER_UPDATE_PRIVATE_KEY_B64` prüfen.
2. Production-Environment mit Freigaberegeln prüfen.
3. Vollständige Windows-/Linux-CI einschließlich PySide6-GUI-Smoke, Ruff und Bandit ausführen.
4. Erst nach grüner Matrix den Tag `v0.3.05` erzeugen und Signaturen/Hashes des resultierenden Releasebundles prüfen.

## Freigabeentscheidung

- **Quellcode / interne RC:** freigegeben.
- **Unsignierte Testartefakte:** nur intern.
- **Öffentliches bzw. Enterprise-Binärrelease:** bis Abschluss der vier externen Schritte gesperrt.
