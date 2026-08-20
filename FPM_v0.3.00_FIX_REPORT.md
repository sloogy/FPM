# FountainPen Manager v0.3.00 – Merge- und Fehlerbehebungsbericht

## Ausgangslage

v0.2.99 brachte den erneuten Start von Tour und Einrichtungsassistent, war aber nicht vollständig auf dem Enterprise-Stand v0.2.98 aufgebaut. Ein direktes Weiterführen hätte responsive Dialoge, schmale Einstellungen, Dashboard-Härtungen, den Datenbank-Lifecycle und mehrere Release-Gates zurückgestuft.

## Merge-Entscheidung

- **Basis:** v0.2.98 Enterprise Responsive UI Hardening
- **Portiert:** Onboarding-Rerun aus v0.2.99
- **Neue Version:** v0.3.00 Onboarding Enterprise Merged

## Umgesetzte Änderungen

### Onboarding

- Force-Flag für den nächsten Tourstart.
- Tourreset funktioniert auch bei vorhandenen Daten und Beispieltinten.
- Einrichtungsassistent kann sofort aus den Einstellungen gestartet werden.
- Gemeinsamer Wizard-Einstiegspunkt in `MainWindow`.
- Tour und Wizard löschen das Force-Flag nach erfolgreichem Abschluss.
- Tourfehler fällt auf den responsiven Wizard zurück.
- DE/EN/FR-Texte und Handbücher aktualisiert.

### Beibehaltene Enterprise-Fixes

- zentrale `ResponsiveDialog`-Basis,
- schmale Einstellungsnavigation und responsiver Button-Reflow,
- sichtbare Kachelaktion „Im Reiter öffnen“,
- verzögerter Dashboard-Reflow,
- kontrastreichere Sekundärtexte,
- sauberer SQLAlchemy-/SQLite-Lifecycle,
- Schutz ungespeicherter Füllerdaten,
- Locale-/Währungs- und Einheitenparser,
- Coverage- und Ruff-Gates.

### Neue Sicherheitsfixes

- URL-Bildimport akzeptiert nur sichere, global routbare HTTP(S)-Ziele.
- Private, lokale, reservierte und Credential-URLs werden blockiert.
- Redirects und finale URL werden erneut geprüft.
- MIME-Typ muss ein Bild sein.
- Legacy-Migration verwendet nur feste SQL-Anweisungen.
- Bandit ist Release-Gate für mittlere und hohe Findings.

### Neue Regressionstests

- Onboarding-Force-Flag und Abschlussverhalten,
- Wizard-Start aus Einstellungen,
- zentraler Wizard-Pfad,
- dreisprachige Onboarding-Schlüssel,
- lokale/private URL-Abweisung,
- gemischte DNS-Auflösung,
- globale Zieladresse,
- erweiterte KILLCRITIC-Invarianten.

## Ergebnis

Der neue Stand enthält die gewünschte v0.2.99-Funktion, ohne die v0.2.98-Härtungen zurückzunehmen. Alle automatisierten Releaseprüfungen und visuellen Offscreen-Stichproben sind bestanden.
