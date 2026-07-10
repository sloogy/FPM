# FountainPen Manager v0.2.87

FountainPen Manager ist eine lokale Desktop-App zur Verwaltung von Füllern, Tinten, Federn, Papier, Schreibproben, Rotation, Ausgaben, Wishlist, BudgetManager-Brücke und Sammler-Insights.

## Release-Fokus v0.2.87

v0.2.87 ist das Ergebnis einer tiefen kritischen Release-Analyse. Sie hat zwei echte Fehler zutage gefördert, die kein bestehendes Audit erfasst hatte.

Der echte GitHub-Releasepfad bleibt gesetzt: `https://github.com/sloogy/FPM/releases`.

📖 **Ausführliches Benutzerhandbuch:** [`docs/BENUTZERHANDBUCH_DE.md`](docs/BENUTZERHANDBUCH_DE.md) – der detaillierte Leitfaden zu allen Funktionen (Score-Formel, Standzeiten, Recherche, Referenztabellen, FAQ).

### Wichtigste Änderungen

- **KRITISCH behoben – Datenverlust:** Ein fehlgeschlagener Bild-Import (Timeout, Netzfehler, „Datei zu groß", fehlende Schreibrechte) lief innerhalb der offenen Transaktion vor dem Commit. Die Exception landete im generischen `except` → Rollback. Der Nutzer verlor **den kompletten frisch eingetippten Füller bzw. die Schreibprobe**, weil ein kosmetischer Bild-Download scheiterte. Der Import ist jetzt nicht-fatal: Rohpfad bleibt erhalten, Daten werden gespeichert, ein Hinweis erscheint **nach** dem Commit.
- **Behoben – Kaskade war keine:** Der „Kein sicherer Treffer"-Dialog öffnete nur **eine** URL, die Bildersuche zwei. Die fachlich wichtige zweite Stufe wurde gebaut, aber nie geöffnet. Jetzt öffnen beide Pfade einheitlich die ersten zwei Stufen; das Handbuch beschreibt das Verhalten korrekt (vorher behauptete es drei Tabs).
- **Ergänzt:** `session.rollback()` im Fehlerpfad von `_add` (fehlte); zwei überzählige Warn-Aufrufe in Methoden ohne Bildimport entfernt.
- **Verifizierte Nicht-Findings** (dokumentiert statt „phantom-gefixt"): Slug/Pfad-Containment des Media-Service sind ausbruchssicher; `reset_all_data` prüft Containment korrekt; der Größenvergleich kann nicht durch Null teilen (Nulllängen werden vorher gefiltert); `_download_to` ist nur über den http/https-Zweig erreichbar.
- **Absicherung:** 10 neue Tests (davon 5 echte Verhaltenstests gegen den Media-Service), 6 neue KILLCRITIC-Invarianten (76 × 20 = 1520 Checks). Die neuen Guards wurden gegen eine künstlich zurückgenommene Korrektur geprüft und schlagen dann nachweislich fehl.

## Wichtigste Änderungen

- **Maße suchen – KI zuerst:** 1. Google-KI-Prompt (`udm=50`), 2. Hersteller-Domain(s), 3. klassische Web-Suche. Die KI-Übersicht trägt technische Daten aus mehreren Quellen zusammen; die Herstellerstufe bleibt als belastbare Primärquelle direkt dahinter.
- **Bilder suchen – Hersteller zuerst:** 1. Hersteller-Bildersuche, 2. KI-Prompt, 3. offene Bildersuche. Bei Produktfotos zählt die offizielle Quelle (Farbe, Finish, aktuelle Ausführung).
- **Automatischer Lookup unverändert hersteller-zuerst** – er liest Seiten mit dem eigenen Parser, dort gibt es keine KI-Übersicht.
- `site:`-Stufen bleiben minimal (nur Modellname) – der Nulltreffer-Bug aus dem Meldefall Essetio bleibt behoben.
- Neuer Reihenfolge-Guard im KILLCRITIC-Audit (70 Invarianten, 1400 Checks): prüft quelltextnah, dass die KI-Stufe bei Maßen **vor** und bei Bildern **nach** der Hersteller-Stufe steht; nachweislich diskriminierend (vertauschte Reihenfolge schlägt fehl).

## Wichtigste Änderungen

- **Neu: Visueller Größenvergleich** – stilisierte Silhouetten mehrerer Füller, Modi *Überlagert* / *Zeilen*, Metriken *Beste verfügbare / Geschlossen / Ohne Kappe / Aufgesteckt*, mit Lineal. Füller ohne passenden Messwert werden übersprungen statt geraten.
- **Neu: Verwaltete Medienablage** (`logic/media_storage_service.py`) – strukturierte Ordner unter `media/` im Datenverzeichnis, 15-MB-Obergrenze, Pfad-Ausbruch-Schutz; Bild- und Schreibproben-Import nutzen sie.
- **Neu: Google-KI-Suchstufe** (`udm=50`) mit natürlichsprachigem Prompt; fällt automatisch auf normale Google-Suche zurück, wenn der KI-Modus nicht verfügbar ist.
- **Bugfix (Root-Cause):** Die `site:`-Suchen waren mit der vollen Suchphrase (im 0.2.84-Zweig zusätzlich mit Exact-Phrase-Quoting) überladen und lieferten strukturell **null Treffer** – gemeldeter Fall Faber-Castell Essetio. Jetzt tragen alle `site:`-Phasen nur den Modellnamen; die Voll-Phrase bleibt der offenen Netzphase vorbehalten.
- **Anforderung „erst Hersteller" wiederhergestellt:** Manuelle Maße- und Bildersuche laufen als **dreistufige Kaskade** – Hersteller-Domain(s) → Google-KI-Prompt → klassische Web-/DDG-Suche. Der 0.2.84-Zweig hatte `site:` ersatzlos entfernt.
- **Stabilerer Auto-Endpunkt:** `html.duckduckgo.com/html/` für den automatischen Lookup.
- Handbuch um Kap. 6.6 (Größenvergleich) und 6.7 (Verwaltete Medien) erweitert, Kap. 17 auf die Kaskade umgeschrieben. KILLCRITIC-Audit auf 69 Invarianten (1380 Checks).

## Wichtigste Änderungen

- **Root-Cause behoben (Merge-Regression aus 0.2.80):** `site:`-Phasen (manuelle Maße-/Bildersuche **und** automatischer Online-Lookup) suchen jetzt bewusst minimal – nur mit dem Modellnamen (`site:faber-castell.com Essetio`). Marke ist durch die Domain gegeben; die Voll-Phrase „dimensions ink capacity filling system" bleibt der offenen Netzphase vorbehalten. Fallback ohne Modell: Marke.
- **Bildersuche entschlackt:** Das tote Pflichtwortpaar „product image" entfällt auch in der offenen Phase (Suchwörter müssen im Seitentext stehen); dort gilt jetzt Marke + Modell + „fountain pen".
- **Stabilerer Auto-Endpunkt:** automatischer Lookup nutzt `html.duckduckgo.com/html/` (weniger Anomalie-/JS-Umleitungen).
- **Verifiziert:** Parser versteht deutsche Herstellerseiten bereits korrekt („Länge geschlossen: 14,4 cm" → 144 mm, Konfidenz 0.91) – der Fehler lag allein in den Queries.
- 3 neue Regressions-Guards (exakter Screenshot-Fall Essetio, Verbotswörter in site-URLs, Endpunkt), KILLCRITIC-Audit +4 Invarianten (61 × 20 = 1220), Handbuch Kap. 17.2/17.3 präzisiert.

## Wichtigste Änderungen

- **Neues Handbuch (24 Kapitel):** Grundphilosophie, Datenverzeichnis & portabler Betrieb (`FPM_DATA_DIR`), alle 14 Module, Dashboard-Semantik, komplette **Score-Formel mit Werkswerten** (Leer-Bonus +120, Standzeit-Staffeln, Farbfamilie +14/−18, Blockade-Deckel −50, Jitter ±140 …), zweistufiges Auswahlverfahren mit Diversitätslayer, Reroll- und Zufallsmechanik, Regel-Engine samt der 8 Standardregeln, Full-Auto-Entscheidungslogik, **Standzeit-Berechnung** (28/14/10/21 Tage, Minimum-Prinzip, Tinten-Individualwert), Hersteller-Recherche inkl. Overlay-Spezifikation, alle 9 Einstellungsseiten, Backup/Umzug, FAQ, Referenztabellen (Settings-Schlüssel, Regeln, Score) und Glossar.
- **Doku-Drift wird Testfehler:** Neuer Guard `tests/test_user_manual_0282_static.py` (10 Tests) prüft die Handbuch-Zahlen **gegen den Code** – Standzeiten gegen das DB-Seeding, Score-Gewichte gegen die Engine, Regelnamen, Rollenliste, Dateinamen und Settings-Referenz. Ändert sich ein Werkswert, schlägt der Build an, bis das Handbuch nachzieht.
- **Verankerung:** README verlinkt das Handbuch prominent; die Hilfe erhält im Schnellstart eine Karte „📖 Ausführliches Handbuch" (DE/EN/FR) mit Fundort.
- KILLCRITIC-Audit auf 57 Invarianten erweitert (Handbuch existiert + ist verlinkt): 1140 Checks, 0 Findings.

## Wichtigste Änderungen

- **Neuer Hilfe-Tab „Rotation & Vorschläge"** (direkt nach dem Schnellstart): Workflow, Score-Ampel lesen, Reroll („nochmal klicken = andere Paare"), Zufallsregler inkl. Sicherheitsgrenze, 💍 feste Paarung & ⭐ Pflicht-Füller.
- **Neuer Hilfe-Tab „Recherche & Daten":** Hersteller-zuerst-Suche erklärt, Quellen-Labels (`manufacturer:` / `online:` / `cache`) entschlüsselt und das Nutzer-Overlay `manufacturer_domains.json` erstmals dokumentiert – mit kopierbarem JSON-Beispiel (String oder Liste je Marke).
- **Schnellstart erweitert:** Schritt 5 führt vom Datenanlegen zum eigentlichen Nutzen („💡 Vorschläge" klicken, per Klick befüllen); neue Karte „Das Dashboard lesen" erklärt die 4 Karten, die Bestandszeile und warum der Safety-Timer nur Fälliges zeigt.
- **Glossar 6 → 12 Begriffe:** EDC, Vac/Vacuum, 💍 Feste Paarung, ⭐ Pflicht-Füller, Harte/weiche Regel, Reroll.
- **Hilfe-Untertitel** beschreibt jetzt den vollen Umfang (Regeln + Vorschläge + Recherche) statt nur die Regel-Engine.
- **Tooltip am „💡 Vorschläge"-Button** erklärt das Reroll-Verhalten direkt am Ort des Geschehens.
- **Neuer Guard `tests/test_help_coverage_0281_static.py`:** 8 Tests stellen sicher, dass Hilfe-Kapitel, Glossar und Tooltip in allen drei Sprachen existieren und substanziell bleiben – künftige Features können nicht mehr „ohne Wiki" landen. KILLCRITIC-Audit auf 54 Invarianten erweitert.

## Wichtigste Änderungen

- **Hersteller zuerst (vereinigt):** ~46 Marken, **mehrere Domains je Marke** (z. B. Pilot EU/US, Sailor int./JP); token-basiertes Längster-Treffer-Matching ohne Substring-Fehltreffer; Nutzer-Overlay `manufacturer_domains.json` (String **oder Liste** je Marke); Online-Lookup mit Phasenplan, striktem Domain-Linkfilter (inkl. Subdomains), Quellkennzeichnung `manufacturer:<host>`, Hersteller-Priorität in der Sortierung und Early-Stop ab Konfidenz ≥ 0.65.
- **Reroll (vereinigt):** harte Sperre auf **(Füller, Tinte)-Paare** statt globaler Tintensperre – erneutes Klicken auf „💡 Vorschläge" zeigt garantiert andere Paare, dieselbe Tinte bleibt für andere Füller verfügbar; Pro-Füller-Rundenneustart (🔁) bei erschöpftem Pool; feste Paarungen 💍 ausgenommen.
- **🎲 Zufälligkeit als Prozentregler (0–100 %)** statt An/Aus: 0 % = reine Bewertung, 100 % = echter Zufall unter sicheren Kandidaten. Blockierende harte Regeln und Full-Auto-Rejects sind in jedem Zufallsgrad tabu; 💍/⭐ werden strukturell über Pass 1 der Auswahl garantiert (nicht nur über Boni).
- Einstellungen → „Rotation & Vorschläge": Prozent-Spinbox mit Tooltip, Duplikat-Checkbox, Warn- und Reroll-Erklärnote; Sofort-Refresh nach Speichern.
- **Dashboard entschlackt:** 4 statt 7 Karten + kompakte Bestandszeile, Safety-Timer nur fällig/bald fällig (≥ 80 %), Advisor 6 / Aktivität 8 Zeilen, Zähler in Abschnittstiteln, kompaktere Tabellenhöhen.
- **Vorschlagsliste lesbar:** kompakte Hinweisspalte (alle Regelwarnungen + 2 Hinweise, Rest „… +N"), mehrzeiliger Tooltip, Score-Ampel, einzeilige Zeilen, Zufalls-Prozentanzeige in der Zusammenfassung.
- **Regelseite klarer:** Kurzlogik-Panel ganz oben (auf jedem Tab sichtbar), Warnstufen-Filter, übersetzte Typ-/Stufen-Labels; i18n-Leak „Nein (Gruppe aus)" behoben.

## Wichtigste Änderungen

- **Hersteller zuerst:** Dimensions- und Bildersuche starten mit einer `site:`-Suche auf der bekannten Hersteller-Domain (~30 Marken, per `manufacturer_domains.json` im Datenverzeichnis erweiterbar); Online-Treffer vom Hersteller werden als `hersteller:<domain>` markiert und bevorzugt. Offenes Netz bleibt Stufe 2.
- **Reroll:** Erneutes Klicken auf „💡 Vorschläge" meidet die Tinten der vorherigen Runden; ist der Pool eines Füllers erschöpft, startet für ihn automatisch eine neue Runde (🔁).
- **🎲 100 % Zufallsmodus** (Einstellungen → Rotation & Vorschläge): Auswahl ignoriert das Scoring, blockierende harte Regeln (z. B. Vac + Shimmer) bleiben aktiv; feste Paarungen 💍 und Pflicht-Füller ⭐ werden respektiert.
- Setting „gleiche Tinte in mehreren Füllern" ist jetzt sichtbar in der UI statt nur in der Datenbank.
- **Dashboard entschlackt:** 4 statt 7 Karten (+ kompakte Bestandszeile), Safety-Timer zeigt nur Fälliges/bald Fälliges (≥ 80 %), Advisor auf 6 und Aktivität auf 8 Zeilen gekürzt, Zähler in den Abschnittstiteln.
- **Vorschlagsliste lesbar:** Hinweisspalte kompakt (Regelwarnungen + 2 Hinweise, Rest per Tooltip/Score-Dialog), Score-Ampelfarben.
- **Regelseite klarer:** Klartext-Erklärung (hart/weich, Warnstufen, Override-Prinzip), Warnstufen-Filter, übersetzte Typ-/Stufen-Labels; i18n-Leak „Nein (Gruppe aus)" behoben.

## Enthaltene Kernbereiche

- Füller-, Tinten-, Feder- und Papierverwaltung
- Schreibproben-Modul mit Vergleichsansicht
- Optionales Enthusiasten-Lab
- Tinten-Restmengen und Nachkauf-Logik
- Feder-Tausch-Historie über `pen_nib_setups`
- Farbfamilien-Lückenanalyse
- Reinigungsprotokoll mit Aufwandsstatistik
- Sammlungswert, Budgetampel und CSV-Exporte
- BudgetManager-JSONL-Export und Sparzielanzeige
- DE/EN/FR i18n

## Validierung

Für den Release wurden folgende Prüfungen verwendet:

```bash
python -m compileall -q .
python -m pytest -q -ra
python tools/sync_version.py --check
python tools/i18n_audit.py
python tools/i18n_quality_audit.py
python tools/i18n_key_wiring_audit.py
python tools/i18n_runtime_audit.py
python tools/i18n_visible_text_audit.py
python tools/gui_smoke_test.py
```

Hinweis: `tools/gui_smoke_test.py` wird nur vollständig ausgeführt, wenn PySide6 in der Umgebung installiert ist. Ohne PySide6 beendet er sauber mit `SKIP`/Returncode `77`.

## Empfohlener Tag

`v0.2.87`

## Wichtige Release-Dokumente

- `CHANGELOG_0.2.87_RELEASE_AUDIT.md`
- `RELEASE_REPORT_v0.2.87_RELEASE_AUDIT.md`
- `docs/GUI_SMOKE_TEST_DE.md`
- `docs/WINDOWS_RELEASE_DE.md`
- `docs/WINDOWS_RELEASE_EN.md`
- `docs/WINDOWS_RELEASE_FR.md`
