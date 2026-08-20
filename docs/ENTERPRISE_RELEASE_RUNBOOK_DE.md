# Enterprise-Release-Runbook v0.3.05

## 1. Einmalige Repository-Einrichtung

1. GitHub-Environment `production` anlegen und bei Bedarf eine Freigabeperson hinterlegen.
2. Branchschutz für die Enterprise-Release-Checks aktivieren.
3. Für diesen Release keine Signier-Secrets hinterlegen. Windows-Artefakte und LifePlanner-/LiveManager-Module werden ausdrücklich unsigned gebaut.

## 2. Plattform-Locks prüfen

`constraints-linux.lock` und `constraints-windows.lock` sind Bestandteil des Release-Candidates. `python tools/gen_lockfile.py --check --platform all` muss grün sein. Nur bei geänderten Abhängigkeiten den Workflow **Generate platform dependency locks** starten und dessen PR nach grüner Prüfung mergen.

## 3. Releasekandidat prüfen

- Enterprise Release Check unter Windows und Linux vollständig grün.
- Ruff, Bandit, komplette Pytest-/Coverage-Suite und GUI-Smoke grün.
- Versionen und Templates mit `python tools/sync_version.py --check` synchron.
- Keine lokalen Änderungen und keine Platzhalter-Hashes im gebauten `latest.json`.
- Den nächsten freien nummerierten RC-Tag setzen (`v0.3.05-rc.2`). Er startet die echten Windows-/Linux-Builds, den Inno-Setup-Installer und beide LifePlanner-Module ohne Signier-Keys.
- Der Workflow veröffentlicht die RC-Artefakte ausdrücklich als unsigned GitHub-Prerelease. Er erzeugt kein `latest.json` für automatische Updates. Die beiden `.lpmodule` enthalten keine `component.json.sig`; LifePlanner/LiveManager behandelt sie wie lokale Unsigned-Pakete und verlangt bei der Installation eine ausdrückliche Vertrauensbestätigung.
- Portable Windows, Portable Linux, Installer und beide `.lpmodule` auf sauberen Testsystemen prüfen. Bei Korrekturen `rc.3`, `rc.4` usw. verwenden und bestehende Tags nicht verschieben.

## 4. Release erzeugen

Nach erfolgreichem RC-Test den finalen Tag `v0.3.05` auf den geprüften Commit setzen. Der Releaseworkflow baut Windows/Linux genau einmal, erzeugt daraus beide `.lpmodule` mit `--allow-unsigned`, verifiziert und testinstalliert sie wie ein LifePlanner-/LiveManager-Host, baut Portable-Pakete und den unsigned Windows-Installer und veröffentlicht anschließend **alle Assets in genau einem Publishjob**. `UNSIGNED_RELEASE.txt` und die Releasebeschreibung weisen ausdrücklich auf die fehlenden Signaturen hin.

## 5. Nachkontrolle

- Windows-EXE und Installer sind erwartungsgemäß nicht Authenticode-signiert und als unsigned gekennzeichnet.
- Alle Einträge in `SHA256SUMS.txt` stimmen mit den Releaseassets überein.
- `latest.json` verweist exakt auf Tag `v0.3.05` und alle Standalone-/Installer-/LifePlanner-Assets.
- Beide `.lpmodule` enthalten keine `component.json.sig` und bestehen die Host-Verifikation/-Testinstallation mit `--allow-unsigned`.
- Portable Windows, Portable Linux und Installer jeweils auf sauberem Testsystem starten.
- Update von der vorherigen stabilen Version auf v0.3.05 testen, inklusive Datenbankbackup und Rollbackdatei.

Bei einem Fehler Tag/Release nicht nachträglich überschreiben, sondern Ursache beheben und eine neue Patchversion veröffentlichen.
