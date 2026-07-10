# Release Report v0.2.79 – Manufacturer-first Release UX & Random Rotation

## Releasefähigkeit

Status: **Release Candidate / gut releasefähig mit manueller UI-Endprüfung**.

Die Version ist technisch stabiler als v0.2.78 und behebt mehrere UX-Blocker, die vor einem öffentlichen Release störend wären. Die Kernlogik kompiliert, die Testbasis läuft vollständig durch und die neuen Online-/Rotationsänderungen sind konservativ umgesetzt.

## Geprüfte Risikobereiche

### Online-Referenzdaten

Befund aus v0.2.78: Die Online-Dimensionsabfrage konnte zwar strukturierte Treffer liefern, priorisierte aber nicht explizit Herstellerquellen. Das war für Sammlungsdaten zu unsauber.

Umsetzung v0.2.79:

- Herstellerdomains für gängige Marken hinterlegt.
- Bilder: Hersteller-Suche zuerst, danach allgemeine Bildsuche.
- Dimensionen: Hersteller-Suche zuerst, danach allgemeine Suche.
- Online-Parser bleibt konservativ: keine geratenen Werte ohne klare Labels und Einheiten.
- Gute Hersteller-Treffer stoppen die breitere Suche.

Resthinweis: Nicht jede Marke hat gut crawlbare Herstellerseiten. In solchen Fällen fällt die App korrekt auf allgemeine Suche oder manuelle Übernahme zurück.

### Dashboard

Befund: Zu viele Karten und Tabellen machen das Dashboard trotz versteckter Leerbereiche schwer lesbar.

Umsetzung:

- Dashboard stärker als Aufmerksamkeitsseite statt Vollreport.
- Safety-Timer zeigt nur relevante/nahe fällige Einträge.
- Aktivität und Advisor begrenzt.
- 0-Warnkarten verschwinden.

### Tintenvorschläge / Rotation

Befund: Die Vorschlagsübersicht war durch lange Warntexte unübersichtlich. Außerdem brachte erneutes Generieren oft dieselben Kombinationen.

Umsetzung:

- Kurze Hinweiszelle + volle Erklärung im Tooltip/Why-Dialog.
- Vorherige Füller-Tinten-Paare werden beim erneuten Generieren deutlich abgewertet.
- Neuer sicherer Zufallsmodus von 0–100 %.
- Hard/Block-Regeln bleiben auch bei 100 % Zufall ausgeschlossen.

### Regeln und Einstellungen

Befund: Regeln, Auto-Mode und Einstellungen waren funktional, aber nicht klar genug erklärt.

Umsetzung:

- Neue Rotationseinstellungsseite statt versteckter Einzeloption.
- Regeln-Seite mit Kurzlogik: harte Regeln, weiche Regeln, Auto-Mode, Override.
- I18N für DE/EN/FR ergänzt.

## Calibre-Prinzip

Die Umsetzung orientiert sich am sinnvollen Calibre-Muster: links klare Bereiche, oben wenige Hauptaktionen, Listen kompakt, Details erst bei Bedarf per Tooltip/Dialog. Das wurde nicht als 1:1-Kopie umgesetzt, sondern als UX-Leitlinie für weniger Überladung.

## Testprotokoll

```text
python -m py_compile / compile pass
python -m pytest -q
150 passed
python tools/sync_version.py --check
Alle Versionsdateien synchron: 0.2.79
```

## Release-Urteil

**Freigabe: RC-fähig.**

Vor endgültiger Veröffentlichung sollte noch ein manueller GUI-Smoke-Test erfolgen:

1. Neuer Füller → Bildsuche öffnet Hersteller-Suche zuerst.
2. Neuer Füller → Dimensionen suchen → Hersteller-Treffer prüfen.
3. Rotation → Vorschläge zweimal klicken → zweite Liste variiert.
4. Einstellungen → Rotation & Vorschläge → Zufall 100 % setzen → keine blockierten Kombis sichtbar.
5. Dashboard mit echter Sammlung prüfen: wirkt deutlich weniger voll.
