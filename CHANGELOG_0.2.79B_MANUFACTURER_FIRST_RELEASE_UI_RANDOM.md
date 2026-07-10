# Changelog v0.2.79 – Manufacturer-first Release UX & Random Rotation

## Fokus

v0.2.79 macht die vorherige Online-Dimensionsabfrage release-tauglicher und räumt zentrale Bedienflächen auf. Herstellerquellen haben jetzt Priorität, die Rotationsvorschläge sind kompakter, erneutes Generieren vermeidet vorherige Paare und ein sicherer Zufallsmodus ist einstellbar.

## Änderungen

### Hersteller zuerst

- Bildsuche nutzt bei bekannten Marken zuerst herstellerbeschränkte Such-URLs.
- Dimensions-/Referenzsuche nutzt ebenfalls Herstellerdomains zuerst, danach allgemeine Websuche.
- Online-Lookup bricht bei guten Hersteller-Treffern vor Shop-/Forum-Rauschen ab.
- Hersteller-Treffer werden im Vorschlag als `manufacturer:*` gekennzeichnet.

### Rotation / Befüllroutine

- Beim erneuten Klick auf „Vorschläge“ werden vorherige Füller-Tinten-Paare deutlich nach hinten sortiert.
- Neuer Einstellungswert `rotation_randomness_percent` von 0–100 %.
- 100 % Zufall wählt zufällig unter sicheren Kombinationen.
- Blockierende/hart schädliche Regeln und Auto-Reject-Kombinationen werden auch bei 100 % Zufall nicht vorgeschlagen.
- Vorschlagsübersicht zeigt kurze Hinweise; volle Erklärung liegt im Tooltip/Score-Dialog.

### Dashboard / UI

- Dashboard zeigt Safety-Timer nur noch als Aufmerksamkeitsliste: überfällige oder bald fällige Einträge.
- Letzte Aktivität reduziert von 20 auf 8 Einträge.
- Sammlungs-Advisor reduziert von 12 auf 6 Einträge.
- Warn-/Service-/Archivkarten werden ausgeblendet, wenn sie 0 sind.
- Tabellenhöhen reduziert, damit die Startseite weniger erschlägt.

### Regeln / Einstellungen

- Neue Einstellungsseite „Rotation & Vorschläge“ mit Zufallsanteil und aktiven Tintendubletten.
- Regeln-Seite erhält eine klare Kurzlogik zu harten Regeln, weichen Regeln, Auto-Mode und Override.
- DE/EN/FR-Texte für neue Optionen ergänzt.

## Tests

- Pen-Dimensions-Service um Hersteller-Prioritätsfälle erweitert.
- Gesamttests: `150 passed`.
- Versionssync: `0.2.79`.
