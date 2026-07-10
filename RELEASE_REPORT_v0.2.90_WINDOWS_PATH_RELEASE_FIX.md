# Releasebericht v0.2.90 – Windows-Pfad- und Release-Fix

## Ursache

Im Repository befanden sich versehentlich Dateien mit abschließendem
Leerzeichen im Namen. Linux konnte diese Pfade verwalten, Windows jedoch
nicht. GitHub Actions brach deshalb beim Checkout des Release-Tags ab.

Zusätzlich war die zentrale PyInstaller-Spezifikation durch eine allgemeine
`*.spec`-Regel von Git ausgeschlossen.

## Korrekturen

- Windows-ungültige Pfade entfernt.
- `FPM.spec` ausdrücklich in Git aufgenommen.
- Linux-CI um Qt-, EGL- und Laufzeitabhängigkeiten ergänzt.
- Release- und Packaging-Guards auf v0.2.90 aktualisiert.
- Windows-Artefakte werden aus einem frischen Checkout gebaut.

## Validierung

- 235 Pytest-Tests erfolgreich.
- GUI-Smoke-Test erfolgreich.
- i18n-Audits für Deutsch, Englisch und Französisch erfolgreich.
- KILLCRITIC-Audit ohne Findings erforderlich.
- Windows-Build und GitHub-Release aus Tag v0.2.90 erforderlich.

## Datenkompatibilität

Keine Änderung am Datenbankschema oder Benutzerdatenformat gegenüber v0.2.89.
