# Enterprise-Release-Runbook v0.3.05

## 1. Einmalige Repository-Einrichtung

1. GitHub-Environment `production` anlegen und mindestens eine Freigabeperson hinterlegen.
2. Authenticode-PFX als Base64 in `WINDOWS_SIGNING_CERT_BASE64` speichern.
3. Zertifikatspasswort als `WINDOWS_SIGNING_CERT_PASSWORD` speichern.
4. `LIFEPLANNER_UPDATE_PRIVATE_KEY_B64` als Base64-codierten 32-Byte-Ed25519-Private-Key hinterlegen. Der zugehörige Public Key muss im LifePlanner-Host als vertrauenswürdiger Release-Key konfiguriert sein.
5. Branchschutz für die Enterprise-Release-Checks aktivieren.

## 2. Plattform-Locks prüfen

`constraints-linux.lock` und `constraints-windows.lock` sind Bestandteil des Release-Candidates. `python tools/gen_lockfile.py --check --platform all` muss grün sein. Nur bei geänderten Abhängigkeiten den Workflow **Generate platform dependency locks** starten und dessen PR nach grüner Prüfung mergen.

## 3. Releasekandidat prüfen

- Enterprise Release Check unter Windows und Linux vollständig grün.
- Ruff, Bandit, komplette Pytest-/Coverage-Suite und GUI-Smoke grün.
- Versionen und Templates mit `python tools/sync_version.py --check` synchron.
- Keine lokalen Änderungen und keine Platzhalter-Hashes im gebauten `latest.json`.
- Den nummerierten RC-Tag `v0.3.05-rc.1` setzen. Er startet die echten Windows-/Linux-Builds und den Inno-Setup-Installer ohne Signier-Keys.
- Der Workflow veröffentlicht die RC-Artefakte ausdrücklich als unsigned GitHub-Prerelease. Er erzeugt dabei weder ein `latest.json` für automatische Updates noch LifePlanner-Module.
- Portable Windows, Portable Linux und Installer auf sauberen Testsystemen prüfen. Bei Korrekturen `rc.2`, `rc.3` usw. verwenden und bestehende Tags nicht verschieben.

## 4. Release erzeugen

Erst nach erfolgreichem RC-Test das `production`-Environment und die drei Signier-Secrets konfigurieren. Danach den finalen Tag `v0.3.05` auf den unveränderten geprüften Commit setzen. Der Releaseworkflow baut Windows/Linux genau einmal, attestiert die bereits geprüften Runtime-Bundles per Ed25519, erzeugt daraus die beiden LifePlanner-Module, verifiziert und testinstalliert diese wie ein Host, baut Portable-Pakete und den signierten Windows-Installer und veröffentlicht anschließend **alle Assets in genau einem Publishjob**.

## 5. Nachkontrolle

- Windows-EXE und Installer: `signtool verify /pa /all /v` erfolgreich.
- Alle Einträge in `SHA256SUMS.txt` stimmen mit den Releaseassets überein.
- `latest.json` verweist exakt auf Tag `v0.3.05` und alle Standalone-/Installer-/LifePlanner-Assets.
- Beide `.lpmodule` bestehen die Host-Verifikation mit dem im LifePlanner hinterlegten Public Key.
- Portable Windows, Portable Linux und Installer jeweils auf sauberem Testsystem starten.
- Update von der vorherigen stabilen Version auf v0.3.05 testen, inklusive Datenbankbackup und Rollbackdatei.

Bei einem Fehler Tag/Release nicht nachträglich überschreiben, sondern Ursache beheben und eine neue Patchversion veröffentlichen.
