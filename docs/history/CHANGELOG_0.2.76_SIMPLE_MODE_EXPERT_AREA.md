# Changelog 0.2.76 – Simple Mode / Expert Area

v0.2.76 setzt die offenen DAU-/UI-Punkte aus dem v0.2.75-Audit um.

## Neu

- Persistenter UI-Modus über `AppSettings.ui_navigation_mode`.
- Standard ist `simple`: neue Nutzer sehen nur die Kernmodule.
- Expertenmodus zeigt weiterhin alle 14 Module.
- Seitenleisten-Button zum Umschalten zwischen Einfachmodus und Expertenbereich.
- Einstellung `UI-Modus` in den allgemeinen Einstellungen.
- Dashboard-Schnellstart mit vier primären Aktionen:
  - Füller eintragen
  - Tinte eintragen
  - Füller befüllen
  - Reinigung eintragen

## Gehärtet

- Expert-only-Seiten sind im Einfachmodus nicht per Shortcut oder direkter Navigation erreichbar; sie fallen auf Dashboard zurück.
- GUI-Smoke-Test prüft jetzt beide Navigationsmodi.
- I18N DE/EN/FR für alle neuen UI-Texte ergänzt.
- Versions-/Release-Dateien auf 0.2.76 synchronisiert.

## Nicht geändert

- Keine Expertenfunktion wurde entfernt.
- GitHub-Releasepfad bleibt `https://github.com/sloogy/FPM/releases`.
- `latest.json.template` enthält weiterhin bewusst `PUT_SHA256_HERE`, bis echte Release-Artefakte gebaut sind.
