# Releasebericht v0.2.89 – Packaging- und CI-Fix

## Ursache

Die lokale Datei `FPM.spec` wurde durch die globale Regel `*.spec`
ignoriert. Lokale Tests fanden die Datei, ein frischer GitHub-Checkout
jedoch nicht. Dadurch scheiterten Packaging-Test und Windows-Build.

## Korrekturen

- `FPM.spec` wird ausdrücklich versioniert.
- Linux-CI installiert Runtime-, Qt- und EGL-Abhängigkeiten.
- Release- und KILLCRITIC-Guards wurden auf v0.2.89 aktualisiert.
- Portable ZIP, Installer, Update-Manifest und Prüfsummen verwenden
  weiterhin dieselbe zentrale Versionsquelle.

## Datenkompatibilität

Keine Änderung am Benutzerdatenformat oder Datenbankschema gegenüber
v0.2.88.

## Freigabekriterium

- vollständige Pytest-Suite grün;
- GUI-Smoke-Test grün;
- alle i18n-Audits grün;
- KILLCRITIC-Audit ohne Findings;
- erfolgreicher Windows-Build aus einem frischen GitHub-Checkout.
