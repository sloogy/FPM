# Release Report – FountainPen Manager v0.2.81 USABILITY & HELP HARDENING

## Ergebnis
**Status: Releasefähig als Source-/Portable-Kandidat (RC).**

Auftrag dieser Runde: Usability aus Sicht eines **neuen Nutzers** prüfen (Logik, Übersicht) und das **Wiki (In-App-Hilfe) auf Gründlichkeit** prüfen und Lücken schließen.

## Usability-Analyse: Befund

### Was für neue Nutzer bereits gut funktioniert (Bestand, geprüft)
- **Erststart:** Onboarding-Panel bei leerer Datenbank mit den vier Schnellstart-Aktionen; prominente Tour-Karte mit Start-Button oben in der Hilfe.
- **Einfachmodus als Standard:** nur die sechs Kernbereiche sichtbar; Expertenbereich zuschaltbar – gute Einstiegskurve.
- **Erklärte Oberfläche (seit 0.2.80):** Kurzlogik-Panel auf der Regelseite, Erklärnoten auf der Settings-Seite „Rotation & Vorschläge", Warnstufen mit Icons statt Rohcodes, leerer Vorschlagszustand mit Handlungsaufforderung („Klicke auf Vorschläge …").
- **Übersichtlichkeit:** Dashboard mit 4 Karten + Bestandszeile, Timer als Alarmzentrale, kompakte Vorschlagsspalte – die 0.2.79/0.2.80-Entschlackung trägt.

### Gefundene Lücken (und warum sie neue Nutzer treffen)
1. **Hilfe kannte den Kern-Workflow nicht.** Sechs Tabs (Schnellstart, Regeln, Full-Auto, Service, Verbrauch, Glossar) – aber kein Wort zu Vorschlägen, Score, Reroll, Zufallsregler, 💍/⭐. Ein neuer Nutzer, der „Hilfe" öffnet, fand zur wichtigsten Seite der App nichts.
2. **Hersteller-Recherche komplett undokumentiert.** Weder der Hersteller-zuerst-Ablauf noch die Quellen-Labels (`manufacturer:` …) noch das Overlay `manufacturer_domains.json` standen irgendwo – das Overlay war ohne Doku faktisch unauffindbar.
3. **Quickstart endete vor dem Nutzen.** Schritte 1–4 legen nur Daten an; der Schritt „Vorschläge klicken → befüllen" fehlte.
4. **Dashboard-Erwartung:** Dass der Safety-Timer bewusst nur Fälliges zeigt, konnte ein Neuling als „meine Befüllungen fehlen" fehlinterpretieren – nirgends erklärt.
5. **Glossar zu dünn:** EDC, Vac, 💍, ⭐, hart/weich, Reroll fehlten – genau die Begriffe, die App-Texte verwenden.
6. **Mikro-Lücke:** Der „💡 Vorschläge"-Button verriet sein Reroll-Verhalten nicht (kein Tooltip).

## Umgesetzte Ergänzungen

| Lücke | Maßnahme |
|---|---|
| Kern-Workflow | Neuer Hilfe-Tab **„Rotation & Vorschläge"** (Position 2): 5 Karten – Workflow, Score/Hinweise, Reroll, 🎲 Zufall (inkl. Sicherheitsgrenze), 💍/⭐ |
| Recherche | Neuer Hilfe-Tab **„Recherche & Daten"**: Hersteller-zuerst, Quellen-Labels, **Overlay-Doku mit kopierbarem JSON-Beispiel** (String/Liste) |
| Quickstart | **Schritt 5** ergänzt (Vorschläge → Klick → befüllt) – in DE/EN/FR |
| Dashboard | Neue Startkarte **„Das Dashboard lesen"** (4 Karten, Bestandszeile, Timer-Semantik) |
| Glossar | **6 → 12 Begriffe** (EDC, Vac, 💍, ⭐, hart/weich, Reroll) |
| Button | **Tooltip** am „💡 Vorschläge"-Button (`rotation.generate_tooltip`) |
| Untertitel | Hilfe-Untertitel deckt jetzt Regeln + Vorschläge + Recherche |

Tab-Reihenfolge folgt der Lernkurve: Schnellstart → **Rotation** → Regeln → Full-Auto → Service → Verbrauch → **Recherche** → Glossar.

## Absicherung gegen Rückfall
- **`tests/test_help_coverage_0281_static.py`** (8 Guards): Tabs existieren und sind richtig einsortiert; alle neuen Keys in DE/EN/FR vorhanden und substanziell (Karten > 120 Zeichen); Rotation-Kapitel erwähnt 💍/⭐/🔁/Zufall/Score; Overlay-Doku enthält Dateiname und Listen-Beispiel; Quickstart endet mit Schritt 5; Glossar vollständig; Tooltip verdrahtet; JSON-Beispiel bleibt formatierungssicher (t() formatiert nur mit kwargs – im Widget werden die Karten parameterlos aufgerufen, per Guard fixiert).
- **KILLCRITIC-Audit** um 4 Hilfe-Invarianten erweitert: **54 × 20 = 1080 Checks, 0 Findings**.

## Validierung
```text
python3 -m compileall -q .                 OK
python3 tools/sync_version.py --check      Alle Versionsdateien synchron: 0.2.81
python3 tools/i18n_audit.py                OK (2029 Keys × 3 Sprachen)
python3 tools/i18n_quality_audit.py        OK
python3 tools/i18n_runtime_audit.py        OK
python3 tools/i18n_key_wiring_audit.py     OK
python3 tools/i18n_visible_text_audit.py   OK
python3 tools/killcritic_1000_loop_audit.py OK (54 × 20 = 1080, 0 Findings)
Tests (headless Shim)                      174 passed, 1 failed*
```
\* Bekannter Sandbox-Fail (`test_logic_migration_hardening.py` braucht echtes SQLAlchemy; kein Netz). Kein Code-Defekt.

## Ehrliche Einschränkungen
- **Kein GUI-Smoke-Test möglich** (PySide6 fehlt in der Sandbox). Die neuen Hilfe-Tabs sind syntaktisch, statisch und über i18n-Audits geprüft, aber nicht am Bildschirm gerendert. Manuelle Checkliste: Hilfe öffnen → beide neuen Tabs durchscrollen (HTML-Karten inkl. `<code>`-Beispiel korrekt gerendert?), Glossar-Zeilen 7–12, Tooltip auf „💡 Vorschläge" per Hover, EN/FR-Sprachumschaltung auf beiden neuen Tabs.
- Die **Tour** wurde bewusst nicht angefasst (GUI-kritisch, ohne Smoke-Test zu riskant). Wenn gewünscht, wäre ein Tour-Schritt „Vorschläge & Reroll" ein sinnvoller nächster, separat testbarer Ausbau.
- Usability-Aussagen basieren auf Code-Review, nicht auf Beobachtung echter Nutzer.

## Release-Urteil
**Freigabe empfohlen für v0.2.81 Source/Portable RC** – vorbehaltlich des manuellen GUI-Smoke-Tests (Checkliste oben).
