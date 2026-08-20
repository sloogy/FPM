# FountainPen Manager v0.3.00 – Vergleich, Enterprise-, UI- und Usability-Audit

**Auditdatum:** 20. Juli 2026
**Vergleich:** v0.2.98 Enterprise Responsive UI Hardening gegen v0.2.99 Onboarding Rerun
**Konsolidierter Stand:** v0.3.00 Onboarding Enterprise Merged

## 1. Management Summary

v0.2.99 ergänzt einen sinnvollen erneuten Start von Tour und Einrichtungsassistent. Sie ist jedoch nicht sauber auf dem vollständig gehärteten v0.2.98-Stand aufgebaut und nimmt mehrere zuvor behobene Enterprise-, Laptop- und Release-Fixes zurück. Deshalb wurde v0.2.99 nicht direkt weitergeführt. Stattdessen wurden ihre Onboarding-Funktionen auf den stabileren v0.2.98-Kern portiert.

Während des Audits wurden zusätzlich zwei Sicherheitsprobleme gefunden und behoben: potenziell unsichere Bildimporte aus lokalen beziehungsweise privaten Netzwerkzielen sowie dynamisch zusammengesetztes SQL in einer Legacy-Migration.

**Releaseblocker nach Behebung:** 0
**Offene kritische Fehler:** 0
**Releaseurteil:** Freigabe als lokaler Desktop-Release empfohlen; native Windows-/Linux-Paket-Smoke-Tests bleiben vor öffentlicher Verteilung sinnvoll.

## 2. Quellvergleich

| Kennzahl | v0.2.98 | v0.2.99 |
|---|---:|---:|
| Bereinigte Dateien | 262 | 260 |
| Gemeinsame Dateien | \- | 257 |
| Geänderte gemeinsame Dateien | \- | 54 |
| Nur in v0.2.98 | 5 | \- |
| Nur in v0.2.99 | \- | 3 |

Nur v0.2.98 enthielt unter anderem den vollständigen UI-Härtungstest `test_ui_usability_hardening_0298.py` sowie die zugehörigen Enterprise-Berichte. v0.2.99 ergänzte `ui/responsive.py`, entfernte dabei aber die zentral verwendete `ResponsiveDialog`-Basis aus dem gehärteten Stand.

### Regressionsrisiken in v0.2.99

1. **Responsive Dialogbasis entfernt**
   Zahlreiche große Dialoge verloren die zentral geprüfte Bildschirmbegrenzung, Scrollbarkeit und dauerhaft erreichbare Aktionsleiste.

2. **Schmale Einstellungen teilweise zurückgebaut**
   Der responsive Aktionsbutton-Reflow und Teile der Laptop-Optimierung waren nicht mehr vollständig vorhanden.

3. **Dashboard-Bedienung zurückgestuft**
   Die sichtbare Aktion „Im Reiter öffnen“ war nicht mehr direkt auf jeder Kachel verfügbar. Auch der verzögerte zweite Reflow gegen einen falschen initialen Einspaltenmodus fehlte.

4. **Datenbank-Lifecycle zurückgenommen**
   Der zentrale, idempotente Abschluss von SQLAlchemy-Sessions und SQLite-Verbindungen war nicht vollständig erhalten.

5. **Release-Gates geschwächt**
   Coverage-, Ruff- und Build-Abhängigkeitsprüfungen aus v0.2.98 waren nicht vollständig fortgeführt.

## 3. Übernommene Onboarding-Verbesserungen

- Tour kann unabhängig vom Sammlungsinhalt für den nächsten Start erzwungen werden.
- Einrichtungsassistent lässt sich in den Einstellungen jederzeit sofort öffnen.
- Ein gemeinsamer Einstiegspunkt in `MainWindow` verhindert parallele Wizard-Pfade.
- Tour- und Wizard-Abschluss löschen das Force-Flag zuverlässig.
- Fallback-Assistent startet weiterhin, wenn die Tour nicht aufgebaut werden kann.
- Texte und Handbücher sind in Deutsch, Englisch und Französisch synchronisiert.
- Vorhandene Sammlungsdaten werden durch den Neustart des Onboardings nicht verändert.

## 4. Zusätzlich gefundene und behobene Fehler

### SEC-001 – Bildimport erlaubte lokale und private Netzwerkziele

**Schweregrad:** Hoch
**Status:** Behoben

Der Bildimport über URL konnte theoretisch `localhost`, private IP-Bereiche, Link-Local-Adressen oder Redirects auf interne Ziele ansprechen. Das ist bei einer Desktop-App ein SSRF-ähnliches Risiko und kann lokale Dienste unbeabsichtigt erreichbar machen.

**Korrektur:**

- nur HTTP und HTTPS,
- keine URL-Credentials,
- keine Loopback-, privaten, Link-Local-, reservierten oder nicht global routbaren Ziele,
- DNS-Auflösung muss ausschließlich global routbare Adressen liefern,
- jeder Redirect wird erneut geprüft,
- finale URL und MIME-Typ werden validiert,
- bestehende Größenbegrenzung bleibt erhalten.

### SEC-002 – Dynamische SQL-Fragmente in Legacy-Migration

**Schweregrad:** Mittel
**Status:** Behoben

Eine ältere Schreibprobenmigration setzte Spaltenfragmente dynamisch zusammen. Die Fragmente stammten zwar aus internem Code, erschwerten aber statische Sicherheitsprüfung und erhöhten das Risiko späterer unsicherer Erweiterungen.

**Korrektur:** ausschließlich feste, explizite SQLAlchemy-`text()`-Anweisungen.

### REL-001 – v0.2.99 verlor Enterprise-Regressionstests

**Schweregrad:** Hoch für den Releaseprozess
**Status:** Behoben

Der zentrale v0.2.98-Test für responsive Dialoge, Einstellungen, Dashboard und Kontrast fehlte. Er wurde vollständig beibehalten und um Onboarding- und Security-Tests ergänzt.

### REL-002 – Sicherheitsanalyse nicht als Release-Gate

**Schweregrad:** Mittel
**Status:** Behoben

Bandit ist nun in den Build-Abhängigkeiten und in der Release-CI mit der Schwelle „mittel“ verankert. Der finale Stand enthält keine mittleren oder hohen Bandit-Findings.

## 5. UI-Audit

### Stärken

- platzsparendes Fokus-Kachel-Dashboard mit wichtigsten Informationen als Text,
- sichtbare Aktion „Im Reiter öffnen“ plus Doppelklick-Schnellweg,
- exklusiv erweiterbare Detailtabelle statt mehrerer dauerhaft sichtbarer Tabellen,
- 3/2/1-Spalten-Reflow nach tatsächlicher Viewport-Breite,
- zentrale responsive Dialoge mit Scrollbereich und erreichbaren Aktionen,
- kompakte Einstellungsnavigation bei schmalen Fenstern,
- kontrastreichere Sekundärtexte,
- durchsuchbares, kontextbezogenes Wiki,
- dreisprachige Handbücher,
- Wizard bei 752 × 584 Pixel nutzbarer Dialogfläche vollständig bedienbar.

### Verbleibende UI-Punkte

- Bei extrem schmalen Fenstern um 800 Pixel wirkt die Haupttoolbar weiterhin dicht; ein Überlaufmenü wäre langfristig besser.
- Die Hilfe-Themenleiste verwendet bei sehr geringer Breite Scrollpfeile. Die Wiki-Suche reduziert die Auswirkung.
- Ein vollständiger Screenreader-, High-Contrast- und vergrößerte-Schrift-Test steht noch aus.

## 6. Usability-Audit

### Positiv

- Der Nutzer kann Tour und Einrichtungsassistent getrennt erneut starten.
- Das Zurücksetzen ist nachvollziehbar und löscht keine Sammlung.
- Füllerformular schützt vor verlorenen Änderungen.
- Numerische Werte mit Einheiten und Währungen bleiben bei Seitenwechsel erhalten.
- Einfachmodus reduziert Komplexität; Expertenziele können kontrolliert geöffnet werden.
- Kachel-Dashboard unterstützt Maus, Doppelklick und Tastatur.
- Fehlermeldungen und Warnungen bleiben übersteuerbar; die Engine empfiehlt, der Nutzer entscheidet.

### Verbleibende Usability-Punkte

- „Tour zurücksetzen“ und „Assistent jetzt starten“ sind zwei ähnliche Aktionen. Die Texte erklären den Unterschied, könnten aber später visuell noch stärker gruppiert werden.
- Lange Expertenformulare bleiben trotz Scrollbarkeit informationsreich. Eine schrittweise Aufteilung großer Dialoge wäre langfristig ADHS-freundlicher.

## 7. Enterprise- und Systemaudit

### Kennzahlen

| Kennzahl | Wert |
|---|---:|
| Produktions-Python-Dateien | 59 |
| Produktionszeilen | ca. 23.297 |
| Breite Exception-Handler | 134 |
| UI-Dateien mit direktem Sessionzugriff | 15 |
| TODO/FIXME/HACK | 0 |
| `shell=True` | 0 |
| Größte UI-Klasse | `PenWidget`, ca. 1.253 Zeilen |
| Größte Methode | `DashboardWidget.refresh()`, ca. 309 Zeilen |

### Systemstärken

- Offlinefähige SQLite-/SQLAlchemy-Datenhaltung.
- Idempotenter Datenbank-Lifecycle mit sauberem Session- und Engine-Abschluss.
- Saubere grobe Modultrennung in UI, Logik, Datenbank, i18n und Updater.
- Umfangreiche dreisprachige Laufzeit- und Wiring-Audits.
- Cross-Platform-Buildstruktur für Windows und Linux.
- Versionssynchronisierung, GUI-Smoke, Ruff, Bandit, Coverage und KILLCRITIC als Release-Gates.
- Keine Shell-Ausführung über `shell=True`.
- Bildimport mit Netzwerkziel-, Redirect-, MIME- und Größenprüfung.

### Offene technische Risiken

#### P1 – Geringe Abdeckung kritischer Logikbereiche

Updater-Module liegen teilweise bei 0 %, Regel- und Rotationsengine nur ungefähr im niedrigen 20-%-Bereich. Die Gesamt-Coverage besteht den aktuellen 50-%-Gate, schützt aber kritische Fehlerpfade noch nicht ausreichend.

**Empfehlung:** Verhaltenstests zuerst für harte Regeln, Overrides, Rotationsscoring, Updater-Manifeste und Update-Rollback.

#### P1 – Große, eng gekoppelte UI-Klassen

`PenWidget`, `SettingsWidget`, `DashboardWidget` und umfangreiche Dialoge enthalten weiterhin viel Zustands-, Datenbank- und Darstellungslogik.

**Empfehlung:** Repository-/Service-Schicht, Tabellenmodelle und getrennte Dialogseiten schrittweise einführen.

#### P2 – Breite Exception-Handler

134 breite Handler sind vorhanden. Viele liegen sinnvoll an UI- und Systemgrenzen, einige können jedoch Programmierfehler verdecken.

**Empfehlung:** Bei jeder bearbeiteten Funktion gezielte Ausnahmearten verwenden und unerwartete Fehler mit Kontext zentral protokollieren.

#### P2 – Supply-Chain-Reproduzierbarkeit

Abhängigkeiten sind begrenzt, aber noch nicht vollständig mit Hashes gelockt.

**Empfehlung:** reproduzierbare Constraints-/Lock-Datei für offizielle Builds erzeugen.

#### P2 – Navigation über feste Indizes

Teile der Navigation verwenden weiterhin Seitenindizes.

**Empfehlung:** zentrale `PageId`-Enumeration beziehungsweise Registry für Navigation, Hilfe und App-Modi.

## 8. Bewertung

| Bereich | Bewertung | Urteil |
|---|---:|---|
| UI-Qualität | **9,1/10** | klar, responsiv und laptopgeeignet |
| Usability | **9,3/10** | gute Fokusführung, Onboarding und Fehlerschutz |
| Barrierearme Darstellung | **8,5/10** | Kontrast gut; vollständiger Accessibility-Test fehlt |
| Funktionsstabilität | **9,3/10** | breite Regression und GUI-Smoke grün |
| Sicherheit | **8,7/10** | lokale Architektur und neue Netzwerk-Härtung; kein Penetrationstest |
| Datenhaltung | **9,0/10** | stabiler DB-Lifecycle und sichere Migration |
| Architektur/Wartbarkeit | **7,4/10** | solide Module, aber große UI-Klassen und direkte DB-Zugriffe |
| Test-/Releaseprozess | **9,4/10** | Coverage, Ruff, Bandit, i18n, GUI und KILLCRITIC |
| Enterprise-Gesamtwertung | **8,8/10** | geeignet für den vorgesehenen Offline-Desktop-Einsatz |
| Releasefähigkeit | **9,4/10** | **Freigabe empfohlen** |

## 9. Releaseentscheidung

**FREIGABE EMPFOHLEN.**

Der konsolidierte Stand bewahrt alle Härtungen aus v0.2.98, ergänzt den sinnvollen Onboarding-Neustart aus v0.2.99 und behebt die beim Enterprise-Audit gefundenen Sicherheitsprobleme. Es bestehen keine bekannten Releaseblocker. Vor der öffentlichen Verteilung sollten die nativen Windows- und Linux-Artefakte jeweils kurz auf einem realen Laptop mit Betriebssystem-DPI, Theme und Mehrmonitorwechsel geprüft werden.
