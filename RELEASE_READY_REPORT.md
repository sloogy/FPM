# FPM v0.3.05 – Release-Ready-Status

**Status: ENTERPRISE-HARDENED SOURCE-RC – BINÄRRELEASE FAIL-CLOSED GESPERRT**

## Erfüllt

- [x] Aktiver Bildimport, Referenzsuche und Updater gegen private/localhost/link-local Ziele geschützt
- [x] Redirects und finale URLs erneut validiert; Umgebungs-Proxies deaktiviert
- [x] Reales Abbrechen aktiver Bilddownloads
- [x] Atomare, verifizierte SQLite-Sicherheitsbackups vor Migrationen
- [x] Datenschutzgefiltertes Rotationslogging und Supportbundle ohne Nutzerdaten
- [x] Getrennte Windows-/Linux-Locklogik ohne ungesicherten Fallback
- [x] Releasepublikation von allen Build-/Test-/Installer-Gates abhängig
- [x] Authenticode-Pflicht für Tag-Releases von EXE und Installer
- [x] LifePlanner-Modulbau in dieselbe Enterprise-Pipeline integriert; separate Publish-Pipeline entfernt
- [x] Ed25519-Attestation der geprüften Runtime-Bundles vor Modulbau
- [x] Host-Verifikation und Testinstallation beider `.lpmodule` vor dem Publish
- [x] Tag, App-Version, `module.json`, Updater-Manifest und Assetnamen aus zentraler Versionsquelle synchronisiert
- [x] Version 0.3.05 / Build `enterprise-lifeplanner-pipeline` synchron
- [x] 418 Tests; 75,37 % Kern-Coverage und 86,55 % Updater-Coverage
- [x] Linux-PyInstaller-Onedir gebaut und als Bundle initialisiert
- [x] 139.000 KILLCRITIC-Checks, 0 Findings
- [x] 2.109 Übersetzungsschlüssel × 3 Sprachen konsistent
- [x] `constraints-linux.lock` und `constraints-windows.lock` erzeugt und installationsgeprüft
- [x] Ruff, Bandit, vollständige PySide6-Suite und GUI-Smoke lokal bestanden

## Vor öffentlicher Freigabe zwingend

- [ ] Vollständige GitHub-CI-Matrix unter Windows und Linux ausführen
- [ ] Reales Windows-Signing-Zertifikat konfigurieren
- [ ] `LIFEPLANNER_UPDATE_PRIVATE_KEY_B64` als Release-Secret konfigurieren
- [ ] Signierten Tag-Build `v0.3.05` erzeugen und SHA256/Signaturen verifizieren

Ein fehlender Punkt führt durch die Pipeline automatisch zum Abbruch; es existiert kein ungesicherter Release-Fallback.
