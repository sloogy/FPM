# Changelog 0.2.75 – KILLCRITIC Release/UI Audit Hardening

## Zweck

v0.2.75 härtet den v0.2.74-Stand nach einer kritischen Release-, Usability- und UI-Konsistenzanalyse.

## Änderungen

- README-Referenzen auf nicht vorhandene v0.2.74-Release-Dateien bereinigt.
- `logic/event_bus.py` um einen Headless-Fallback erweitert, damit Logik-/CI-Importe ohne PySide6 nicht an Qt scheitern.
- Regressionstest für README-Dateiverweise ergänzt.
- Regressionstest für EventBus-Fallback ergänzt.
- Version, Manifest-Templates, Windows-Doku, GUI-Smoke-Test-Doku, Installer-Metadaten und i18n-App-Version auf 0.2.75 synchronisiert.

## Nicht geändert

- Keine Änderung an Datenmodell oder Migrationen.
- Keine riskante UI-Umbauaktion ohne echten Qt-/Windows-Smoke-Test.
- GitHub-Releasepfad bleibt: `https://github.com/sloogy/FPM/releases`.
