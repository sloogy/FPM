# Release Report – FountainPen Manager v0.2.82 USER MANUAL

## Ergebnis
**Status: Releasefähig als Source-/Portable-Kandidat (RC).**

Auftrag: Eine ausführliche Dokumentation als Leitfaden **zusätzlich zum Wiki**, in der Funktionen detailliert statt oberflächlich erklärt werden.

## Was geliefert wurde
`docs/BENUTZERHANDBUCH_DE.md` – 24 Kapitel, ~28 000 Zeichen. Der Leitfaden geht bewusst dorthin, wo das Wiki aufhört: konkrete Werkswerte, Formeln, Prioritätslogiken und Referenztabellen. Kernstücke sind die vollständige Score-Aufschlüsselung (Kap. 9.2 mit Tabelle), das zweistufige Auswahlverfahren inkl. Diversitätslayer (9.3), die exakte Standzeit-Berechnung mit Rechenbeispiel (Kap. 12), die Full-Auto-Entscheidungslogik (Kap. 11), die Recherche-Pipeline mit Overlay-Spezifikation (Kap. 17) sowie Referenzteil (Settings-Schlüssel, Standardregeln, Score) und 20-Begriffe-Glossar. Jede Zahl wurde vor dem Schreiben aus dem Code verifiziert – nicht aus dem Gedächtnis übernommen.

## Verankerung
README-Link direkt unter dem Release-Fokus; Hilfe-Schnellstart-Karte „📖 Ausführliches Handbuch" in DE/EN/FR mit Fundort und Hinweis auf Markdown-Lesbarkeit/Druckbarkeit.

## Absicherung: Doku-Drift wird Testfehler
`tests/test_user_manual_0282_static.py` (10 Guards) prüft Handbuch-Aussagen gegen die Code-Quellen: Standzeiten gegen `database/db.py`, Score-Gewichte und Formeln gegen `logic/rotation_engine.py`, Regelnamen kontextgenau aus den `Rule(`-Seeding-Blöcken, Rollenliste gegen `logic/role_config.py`, Schwellen (80 %, 0.65) gegen Dashboard/Recherche, Settings-Referenz gegen das Seeding, plus Existenz-/Umfangs-/Verlinkungs-Checks. Ändert ein künftiger Patch einen Werkswert, bricht die Suite, bis das Handbuch nachzieht.

**Transparenz:** Der Guard bewies seinen Wert sofort gegen seinen Autor – der erste Filter übersah „Pigmenttinte" (case-sensitives Substring-Matching auf „Tinte"). Behoben durch kontextgenaues `Rule(`-Matching; alle 8 Regelnamen werden jetzt exakt verifiziert.

## Validierung
```text
python3 -m compileall -q .                  OK
python3 tools/sync_version.py --check       Alle Versionsdateien synchron: 0.2.82
python3 tools/i18n_audit.py                 OK (2031 Keys × 3 Sprachen)
python3 tools/i18n_quality_audit.py         OK
python3 tools/i18n_runtime_audit.py         OK
python3 tools/i18n_key_wiring_audit.py      OK
python3 tools/i18n_visible_text_audit.py    OK
python3 tools/killcritic_1000_loop_audit.py OK (57 × 20 = 1140, 0 Findings)
Tests (headless Shim)                       184 passed, 1 failed*
```
\* Bekannter Sandbox-Fail (`test_logic_migration_hardening.py`, SQLAlchemy nicht installierbar, kein Netz). Kein Code-Defekt.

## Ehrliche Einschränkungen
- Das Handbuch liegt **nur auf Deutsch** vor (Hauptzielgruppe; Wiki bleibt dreisprachig). EN/FR-Fassungen wären ein sinnvoller, separater Ausbau – die Hilfe-Karte weist EN/FR-Nutzer transparent darauf hin.
- Kein GUI-Smoke-Test möglich (PySide6 fehlt in der Sandbox). Checkliste: Hilfe → Schnellstart → Handbuch-Karte sichtbar (DE/EN/FR), Handbuch in einem Markdown-Viewer öffnen (Tabellen/Links/Anker), Stichproben gegen die App (z. B. Zeiten-Tab-Werte vs. Kap. 12).
- Screenshots fehlen bewusst: Sie veralten schnell und sind headless nicht erzeugbar; das Handbuch beschreibt stattdessen präzise in Worten. Bei Bedarf später ergänzbar.

## Release-Urteil
**Freigabe empfohlen für v0.2.82 Source/Portable RC** – vorbehaltlich des manuellen GUI-Smoke-Tests (Checkliste oben).
