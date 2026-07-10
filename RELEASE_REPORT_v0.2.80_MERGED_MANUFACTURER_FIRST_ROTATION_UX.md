# Release Report – FountainPen Manager v0.2.80 MERGED (Manufacturer First + Rotation UX)

## Ergebnis
**Status: Releasefähig als Source-/Portable-Kandidat (RC).**

Zwei parallel entwickelte 0.2.79-Zweige (A „MANUFACTURER_FIRST_ROTATION_UX", B „MANUFACTURER_FIRST_RELEASE_UI_RANDOM") wurden Thema für Thema verglichen und zur besseren Gesamtlösung vereinigt. Beide Zweigberichte liegen als Historie bei (`*_0.2.79A_*`, `*_0.2.79B_*`).

## Vergleichs- und Merge-Matrix

| Thema | Sieger | Begründung / übernommene Gegenseite |
|---|---|---|
| Herstellerverzeichnis | **B-Struktur** | Tuple je Marke (regionale Domains), 46er-Union beider Listen; A-Overlay bleibt (jetzt mit Listenwerten) |
| Marken-Matching | **A** | Token-Teilmengen + Längster-Treffer; B-Substring hätte „Crossfield"→„cross" gematcht |
| Quellerkennung | **B** | endswith erkennt Subdomains (`shop.pelikan.com`); mit `data_dir`-Overlay verheiratet |
| Online-Lookup | **Merge** | B-Phasenplan + Early-Stop ≥ 0.65 + Hersteller-Sortierung; A-Linkfilter je Herstellerphase (B lud Fremdlinks) + A-Wert-Dedupe |
| Reroll | **Merge** | B-Paarsperre (Tinte bleibt für andere Füller frei) + A-Härte (Exklusion statt −260-Malus, der bei hohen Scores versagt) + A-Kumulation (kein A/B-Ping-Pong) + A-Fallback 🔁 |
| Zufall | **Merge** | B-Prozentregler 0–100 + B-Auto-Reject-Filter + B-`random_delta`; A-Korrektheit: 💍 vom Blockfilter ausgenommen (Override-Prinzip), 💍/⭐ strukturell via Pass 1 garantiert statt wegwürfelbarer +30/+15-Boni |
| Settings-Seite | **B** | Spinbox %, Tooltips, Sofort-Refresh, t()-Nav-Key; + A-Reroll-Erklärnote |
| Dashboard | **A** | B hatte 7 Karten & ungefilterten Timer behalten; B-Tabellenhöhen (150/165) zusätzlich übernommen |
| Vorschlagsliste | **A** | B zeigte nur 1. Eintrag und übersetzte Regelwarnungen nicht; B-`setWordWrap(False)` + mehrzeiliger Tooltip übernommen |
| Regelseite | **Merge** | B-Position (Panel ganz oben, alle Tabs) + A-Substanz (Stufenfilter, Label-Übersetzung, Leak-Fix – Leak war in B noch offen) |
| i18n | **Merge** | B-Settings-Keys, kombinierter `overview_explain`, `{pct}`-Parametrisierung; obsolete Zweig-Keys entfernt, Parität 1999 × 3 |
| Tests | **Merge** | A-Verhaltenstests auf neue Architektur portiert (7 reale Tests), B-URL-Tests integriert, neuer Early-Stop-Test |

## Beim Merge gefundene Zweig-Schwächen (behoben)
1. **B-Zufall konnte feste Paarungen brechen:** Jitter ±140 gegen +30-Bonus; verheiratete Paare mit übersteuertem Blocker flogen ganz raus. Jetzt strukturelle Garantie über Pass 1 der Auswahl, Filter nimmt 💍 aus. Durch Verhaltenstest abgesichert (`test_full_random_keeps_fixed_pairing_structurally`, 10 Läufe).
2. **B-Reroll ohne Garantie:** −260-Malus unterliegt Scores > 260 → gleiche Tinte trotz Klick. Jetzt harte Paar-Exklusion mit Pro-Füller-Fallback.
3. **B-Herstellerphase lud Fremdlinks:** Kandidaten der `site:`-Suche wurden ungefiltert gefetcht. Jetzt strikter Domainfilter (inkl. Subdomains) je Phase; Test stellt sicher, dass Händlerlinks nie geladen werden.
4. **B-Widget zeigte nur erste Warnung** und schickte Regelwarnungen nicht durch die Übersetzung. A-Spalte (alle Warnungen + 2 Hinweise) bleibt; B-Tooltip-Mehrzeiligkeit übernommen.
5. **A-Blockersatz-Regression im Merge selbst:** `_extract_candidate_links`/`_domain_label` wurden beim Umbau mitgelöscht – wiederhergestellt; kompletter Lookup-Testpfad grün.

## Neu/geändert – Dateien
- `logic/pen_dimensions_service.py`, `logic/rotation_engine.py`, `database/db.py`
- `ui/rotation_widget.py`, `ui/settings_widget.py`, `ui/dashboard_widget.py`, `ui/rules_widget.py` (Alt-Hint entfernt), `ui/pen_widget.py` (A-Stand)
- `i18n/de.json`, `i18n/en.json`, `i18n/fr.json`
- `tests/test_rotation_random_and_reroll_0280.py` (neu, ersetzt 0279), `tests/test_pen_dimensions_service.py`, `tests/test_release_hardening_static.py`
- `app_info.py` (Version 0.2.80, Datum 8. Juli 2026, Build `manufacturer-first-rotation-ux-merged`) + alle Versions-/Doku-Dateien
- Historie: `CHANGELOG/RELEASE_REPORT` beider 0.2.79-Zweige als A/B beigelegt

## Validierung
```text
python3 -m compileall -q .                 OK
python3 tools/sync_version.py --check      Alle Versionsdateien synchron: 0.2.80
python3 tools/i18n_audit.py                OK (1999 Keys × 3 Sprachen)
python3 tools/i18n_quality_audit.py        OK
python3 tools/i18n_runtime_audit.py        OK
python3 tools/i18n_key_wiring_audit.py     OK
python3 tools/i18n_visible_text_audit.py   OK (echtes translate_source_text)
Tests (headless Shim)                      166 passed, 1 failed*
```
\* `test_logic_migration_hardening.py` benötigt echtes SQLAlchemy (in der netzlosen Sandbox nicht installierbar). Kein Code-Defekt.

## Ehrliche Einschränkungen
- **Kein GUI-Smoke-Test möglich** (PySide6 fehlt in der Sandbox). Manuelle Checkliste vor Release: Einstellungen → „Rotation & Vorschläge" (Prozent speichern/laden), zweimal „💡 Vorschläge" (andere Paare?), 100 % einstellen und prüfen, dass verheiratete Füller 💍 ihre Tinte behalten, Dashboard-Ansicht, Regelseite (Panel oben, Stufenfilter), Vorschlags-Tooltips.
- **Hersteller-Domains teils unverifiziert** (kein Netz): B-Neuzugänge sind im Code markiert; Fehleinträge degradieren zur offenen Websuche und sind per `manufacturer_domains.json` korrigierbar.
- Kein Windows-Build/Installer-Test in dieser Umgebung.

## Release-Urteil
**Freigabe empfohlen für v0.2.80 Source/Portable RC** – vorbehaltlich des manuellen GUI-Smoke-Tests (Checkliste oben).


---

## Nachtrag (8. Juli 2026): Tiefenvergleich mit parallelem RC „KILLCRITIC_MERGED_RELEASE_CANDIDATE“

Ein zweiter, unabhängiger 0.2.80-Merge derselben 0.2.79-Zweige wurde geprüft (Build `killcritic-merged-release-candidate`). Formal grün (Audits OK, 162/163 Tests), aber im Detail unterlegen:

| Thema | KILLCRITIC-RC | Dieser Stand (M) |
|---|---|---|
| Zufalls-Architektur | Zwei Pfade (1–99 % Jitter + separater 100 %-Würfelpfad) | Ein Pfad, konsistent |
| Sicherheitsfilter | **Fund: 100 %-Pfad filtert Full-Auto-Rejects NICHT** (bei 1–99 % schon) | Reject- und Block-Filter in jedem Zufallsgrad, 💍 ausgenommen; testabgedeckt |
| Legacy-Setting | `rotation_random_mode` wird weitergepflegt und **in frische DBs neu geseedet**, obwohl nie released | Ein Setting (`rotation_randomness_percent`), kein toter Ballast |
| Reroll | Tinten-globale Sperre (Tinte für alle Füller blockiert) | (Füller, Tinte)-**Paar**-Sperre, kumulativ, mit 🔁-Fallback |
| Regelseite | Alt-Hint + Erklärpanel **gestapelt** im Regelliste-Tab | Ein konsolidiertes Kurzlogik-Panel ganz oben (alle Tabs) |
| Settings-Speichern | Kein Sofort-Refresh | `_refresh_all_widgets()` nach Speichern |
| Vorschlagsliste | Ohne Volltext-Tooltip, ohne WordWrap-Off | Mehrzeiliger Tooltip, einzeilige Zeilen |
| Tests | 0279-Suite deckt weder Jitter-Pfad noch Reject-Filter (0 Treffer) | 0280-Suite: 7 reale Verhaltenstests inkl. 💍-Garantie unter 100 % Zufall und Reject-Filter |

**Aus dem RC übernommen:** `tools/killcritic_1000_loop_audit.py` – auf diesen Stand portiert (50 Invarianten × 20 = 1000 Checks). Die neuen Invarianten schreiben genau die RC-Schwächen als dauerhafte Guards fest (Ein-Pfad-Zufall, Reject-Filter, Paar-Sperre, kein Legacy-Seeding). Lauf: **0 Findings**.

**Entscheid:** Dieser Stand (M) bleibt der Release-Kandidat v0.2.80.
