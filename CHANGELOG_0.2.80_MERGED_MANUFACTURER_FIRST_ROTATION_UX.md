# Changelog v0.2.80 – MERGE der Zweige 0.2.79A (Rotation UX) und 0.2.79B (Release UI Random)

Pro Thema wurde die robustere Lösung übernommen; kein Feature einer Seite ging verloren. Zweigberichte liegen als `*_0.2.79A_*` / `*_0.2.79B_*` bei.

## Hersteller-zuerst (Dimensionen & Bilder) – vereinigt
- **Aus B:** `MANUFACTURER_DOMAINS` mit **Tuple je Marke** (mehrere Domains, z. B. Pilot `pilotpen.eu` + `pilotpen.com`), erweiterte Markenliste (u. a. Nakaya, Leonardo, S.T. Dupont, Asvine, Hongdian, Karas), `_is_manufacturer_source()` mit **endswith-Matching** (erkennt Subdomains wie `shop.pelikan.com`), eigener Builder `build_online_dimension_search_urls()`, Early-Stop bei Herstellertreffer ≥ 0.65, Hersteller-Priorität in der Ergebnis-Sortierung.
- **Aus A:** token-basiertes Längster-Treffer-Matching (kein Substring-Fehltreffer „Crossfield“→„cross“; B-Ansatz ersetzt), Nutzer-Overlay `manufacturer_domains.json` (jetzt String **oder Liste** je Marke), strikter **Domain-Linkfilter in Herstellerphasen** (B lud Fremdlinks), Dedupe wertidentischer Treffer, `data_dir`-Durchreichung bis in Pen-Widget-Bildersuche.
- Vereinigte Liste: 46 Marken; offline unverifizierbare B-Domains sind im Code markiert und per Overlay korrigierbar (offene Websuche bleibt letzte Stufe).
- Quellkennzeichnung vereinheitlicht auf `manufacturer:<host>` (B-Konvention).

## Reroll „andere Tinten“ – vereinigt
- **Aus B:** Sperre auf **(Füller, Tinte)-Paare** statt globaler Tinten-IDs – dieselbe Tinte bleibt für andere Füller wählbar.
- **Aus A:** **harte Exklusion** statt −260-Malus (Malus garantiert bei hohen Scores keine neuen Tinten), **kumulatives** Rundengedächtnis statt Nur-letzte-Runde (verhindert A/B-Ping-Pong), Pro-Füller-Fallback mit 🔁-Hinweis, feste Paarungen 💍 ausgenommen.
- B-Key `rotation.hint_previous_suggestion_penalty` entfällt (Malus-Mechanik ersetzt).

## Zufälligkeit – vereinigt
- **Aus B:** Setting **`rotation_randomness_percent` (0–100)** statt binärem Schalter; `SystemRandom`-Jitter-Mischung `score·(100−p)/100 + jitter·p/100`; Filter auch für **Full-Auto-Rejects**; `random_delta` im Score-Dict (Why-Dialog-Transparenz).
- **Aus A (Korrektheit):** blockierende Kombinationen mit **fester Paarung sind vom Filter ausgenommen** (Override-Prinzip; B warf verheiratete Paare weg), 💍/⭐ werden **strukturell über Pass 1** der Auswahl garantiert statt über schwache +30/+15-Boni (bei Jitter ±140 konnte B die feste Tinte wegwürfeln), Zufallsstatus sichtbar in Hinweis **und** Zusammenfassung (jetzt mit Prozentwert: „🎲 Zufall 75 % aktiv …“).
- Alter A-Sonderpfad `_build_random_suggestion_set` und Setting `rotation_random_mode` vollständig entfernt – **ein** Auswahlpfad.
- DB-Seeding: `rotation_randomness_percent = "0"`.

## Einstellungen „Rotation & Vorschläge“ – B-Basis + A-Erklärtiefe
- **Aus B:** Prozent-Spinbox (Schrittweite 5, Suffix %), Tooltips, Warn-Note, defensives Laden, `_refresh_all_widgets()` nach Speichern, Nav-Titel über echten t()-Key.
- **Aus A:** zusätzliche Reroll-Erklärnote (`settings.rotation_reroll_note`).
- A-Keys `settings.rotation.*` (geschachtelt) entfernt; B-Keys `settings.rotation_*` (flach) übernommen.

## Dashboard – A-Basis + B-Kompaktheit
- A: 4 Karten + Bestandszeile, Timer-Filter ≥ 80 %, Advisor 6 / Aktivität 8, Titelzähler (B hatte 7 Karten und ungefilterten Timer behalten).
- B: kompaktere Tabellen-Maximalhöhen (150/150/165/150) zusätzlich übernommen.

## Vorschlagsliste – A-Basis + B-Feinheiten
- A: alle Regelwarnungen sichtbar + max. 2 Hinweise + „… +N“, Score-Ampel, Volltext im Score-Dialog (B zeigte nur den ersten Eintrag und übersetzte Regelwarnungen nicht).
- B: `setWordWrap(False)` (einzeilige Zeilen), Tooltip **mehrzeilig** statt |-Riesenstring.

## Regelseite – B-Position + A-Substanz
- B: Kurzlogik-Panel **ganz oben** (auf jedem Tab sichtbar); Text um A-Inhalte erweitert (Warnstufen-Legende, Doppelklick, Override, Zufallsmodus-Bezug). Redundanter Alt-Hinweis „Regeln sind in Reitern getrennt“ entfernt (Key bleibt erhalten).
- A: Warnstufen-Filter, übersetzte Typ-/Stufen-Labels mit Icons, i18n-Leak-Fix „Ja/Nein/Nein (Gruppe aus)“ (in B weiterhin vorhanden gewesen).
- A-Key `rules.list_explainer` entfällt zugunsten `rules.overview_explain`.

## Technik & Hygiene
- `APP_BUILD = "manufacturer-first-rotation-ux-merged"`, Release-Datum 8. Juli 2026, alle Versionsdateien synchron 0.2.80.
- i18n: 1999 Keys × 3 (netto: B-Settings-Keys +, kombinierter `overview_explain`, parametrisierte Zufalls-Texte mit `{pct}`; obsolete Zweig-Keys entfernt).
- Tests: neue Datei `test_rotation_random_and_reroll_0280.py` (7 reale Verhaltenstests inkl. struktureller 💍/⭐-Garantie unter 100 % Zufall + 8 statische Guards); `test_pen_dimensions_service.py` auf Tuple-API/`manufacturer:` umgestellt, B-Tests integriert, neuer Early-Stop-Test.
- Beim Merge gefunden & behoben: Blockersatz hatte `_extract_candidate_links`/`_domain_label` mitgelöscht (wiederhergestellt, durch Suite abgedeckt).

## Nachtrag (RC-Vergleich)
- Neues Release-Gate `tools/killcritic_1000_loop_audit.py` (aus parallelem KILLCRITIC-RC portiert): 50 Invarianten × 20 Läufe, inkl. Guards gegen die im RC-Vergleich gefundenen Schwächen (Doppelpfad-Zufall, fehlender Auto-Reject-Filter bei 100 %, Tinten- statt Paar-Sperre, Legacy-Setting-Seeding).
