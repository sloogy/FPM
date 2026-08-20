# Changelog v0.2.79 – MANUFACTURER FIRST + ROTATION UX

## Neu

### Hersteller-zuerst-Recherche (Bilder & Dimensionen)
- Neues Hersteller-Verzeichnis `MANUFACTURER_DOMAINS` (~30 etablierte Marken) in `logic/pen_dimensions_service.py`.
- `manufacturer_domain_for_brand()`: token-basiertes Marken-Matching, längster Treffer gewinnt (unterscheidet z. B. „Graf von Faber-Castell“ von „Faber-Castell“).
- Nutzer-Overlay `manufacturer_domains.json` im Datenverzeichnis: eigene Marken ergänzen oder Domains korrigieren – ohne Codeänderung.
- `build_dimension_search_urls()` und `build_image_search_urls()` liefern zuerst eine `site:<hersteller>`-Suche, danach die bisherigen offenen Suchen.
- `lookup_online_dimensions()` arbeitet zweiphasig: Phase 1 nur Herstellerseite (Ergebnislinks auf die Domain gefiltert, Quelle `hersteller:<domain>`), Phase 2 offenes Netz nur bei leerem Herstellerergebnis.

### Rotation: Reroll mit neuen Tinten
- `RotationEngine.get_suggestions(..., avoid_ink_ids=...)`: Tinten früherer Vorschlagsrunden werden gemieden.
- Rotations-Widget merkt sich vorgeschlagene Tinten – jeder Klick auf „💡 Vorschläge“ zeigt andere Tinten als zuvor.
- Automatischer Rundenneustart pro Füller, wenn alle Tinten durch sind (Hinweis 🔁), feste Paarungen 💍 bleiben immer erlaubt.

### 🎲 100 % Zufallsmodus
- Neues Setting `rotation_random_mode` (Standard aus, wird beim DB-Init geseedet).
- Aktiv: Auswahl ignoriert das komplette Scoring und würfelt pro Füller – **ausgenommen füllerschädigende Kombinationen** (blockierende harte Regeln wie Vac + Shimmer).
- Feste Paarungen 💍 und Pflicht-Füller ⭐ werden weiterhin respektiert; jede Tinte/jeder Füller max. 1×.
- Neue Einstellungsseite **„Rotation & Vorschläge“** mit Klartext-Erklärungen; dort ist jetzt auch `rotation_allow_active_ink_duplicates` sichtbar schaltbar (war bisher nur ein DB-Setting).

## Verbessert

### Dashboard entschlackt
- 4 statt 7 Stat-Karten (Aktive Füller, Tinten, Warnungen, Sammlungswert); Bestand/Service/Archiv als kompakte Textzeile mit Tooltip.
- Ink Safety Timer zeigt nur noch überfällige und bald fällige Ladungen (≥ 80 % der Maximaltage) statt aller Befüllungen; Abschnittstitel mit Zählern („x überfällig · y bald fällig“).
- Sammlungs-Advisor auf 6 Zeilen, letzte Einfüllungen auf 8 Einträge gekürzt; Service-&-Sperren-Titel mit Zähler.

### Tintenvorschläge lesbarer
- Hinweisspalte kompakt: Regelwarnungen vollständig + maximal 2 Info-Hinweise, Rest per „… +N Details“, kompletter Text im Tooltip und Score-Dialog.
- Score-Ampelfarben (grün ≥ 100, orange < 0, rot bei blockierender Regel).
- Zufallsmodus wird in der Zusammenfassungszeile klar ausgewiesen.

### Regelseite klarer
- Klartext-Erklärung über der Regelliste: harte vs. weiche Regeln, Warnstufen-Legende, Override-Prinzip („Die Engine empfiehlt – du entscheidest“).
- Neuer Warnstufen-Filter neben dem Gruppenfilter.
- Warnstufe und Regeltyp erscheinen als übersetzte Labels mit Icon statt roher Codes („hard“ → „Hart (Schutz)“).

## Behoben
- i18n-Leak in der Regelliste: „Ja“/„Nein“/„Nein (Gruppe aus)“ in der Wirksam-Spalte waren hartkodiert und erschienen auch in EN/FR auf Deutsch – jetzt echte i18n-Keys.

## Technik
- Neues Score-Dict-Feld `has_blocked` (Basis für Zufallsfilter und Score-Ampel).
- 25 neue i18n-Keys × 3 Sprachen (gesamt 1999 × 3, alle Audits grün).
- 18 neue Tests in `tests/test_rotation_random_and_reroll_0279.py` (reale Zufallslogik via Import-Stubs, statische UI-/i18n-Guards) und 6 neue Tests in `tests/test_pen_dimensions_service.py` (Hersteller-Matching, Overlay, Phasenpriorität).
- `rotation.hint_repeat_round`-Hinweis wird in Wiederholungsrunden vorangestellt.
