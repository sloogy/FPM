# Release Report – FountainPen Manager v0.2.75 KILLCRITIC Release/UI Audit Hardening

## Kurzurteil

v0.2.75 ist ein gehärteter Source-/Portable-Release-Kandidat auf Basis von v0.2.74.

## Hauptbefunde aus dem Audit

- Codebasis kompiliert sauber.
- Testsuite ist grün.
- i18n-Audits sind grün.
- GitHub-Releasepfad ist korrekt auf `https://github.com/sloogy/FPM/releases` gesetzt.
- v0.2.74 enthielt jedoch README-Verweise auf nicht vorhandene Release-Dateien.
- `logic/event_bus.py` hatte eine direkte PySide6-Abhängigkeit, obwohl `logic/rotation_engine.py` den EventBus importiert. Das ist im installierten GUI-Betrieb kein Crash, aber für Headless-Logik-/CI-Prüfungen und Source-Audits unnötig fragil.

## Umgesetzte Härtung

- Fehlende README-Referenzen entfernt/ersetzt.
- Headless-EventBus-Fallback ergänzt.
- Regressionstests für beide Befunde ergänzt.
- Versions-/Release-Dateien auf 0.2.75 synchronisiert.

## Restrisiko

Der echte Qt-GUI-Smoke-Test muss weiterhin auf einer Umgebung mit PySide6 durchgeführt werden. In der Sandbox ohne PySide6 ist der GUI-Smoke-Test erwartbar `SKIP`.

## Freigabe

- Source-/Portable-RC: Ja.
- Öffentlicher Final Release: Ja nach bestandenem manuellem GUI-Smoke-Test.
- Windows-Installer: erst nach Build, SHA256-Manifest und Testinstallation freigeben.
