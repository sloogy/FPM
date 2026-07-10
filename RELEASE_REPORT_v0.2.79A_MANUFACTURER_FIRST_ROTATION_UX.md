# Release Report – FountainPen Manager v0.2.79 MANUFACTURER FIRST + ROTATION UX

## Ergebnis
**Status: Releasefähig als Source-/Portable-Kandidat (RC).**

Ausgangspunkt war v0.2.78 mit sieben gemeldeten Punkten: Release-Prüfung, Hersteller-zuerst für Bilder und Dimensionen, UI-Bedienbarkeit (Dashboard, Tintenvorschläge, Regeln, Einstellungen), Reroll mit neuen Tinten und ein optionaler 100 %-Zufallsmodus. Alle sieben Punkte sind umgesetzt; zusätzlich wurde ein dabei entdeckter i18n-Leak behoben.

## Prüfmatrix

| Thema | Prüfschwerpunkt | Ergebnis |
|---|---|---|
| 1. Basisvalidierung | compileall, dev_check, Versions-Sync | OK, 0.2.79 synchron |
| 2. Hersteller-zuerst Dimensionen | Domain-Matching, Phasenpriorität, Overlay, Quellkennzeichnung | Umgesetzt + 6 Tests |
| 3. Hersteller-zuerst Bilder | site:-Suche zuerst, Overlay-Anbindung im Pen-Widget | Umgesetzt |
| 4. Reroll („andere Tinten“) | avoid_ink_ids, Pro-Füller-Fallback, feste Paarungen ausgenommen | Umgesetzt + Guards |
| 5. 100 % Zufallsmodus | Setting, Schutzregel-Filter, 💍/⭐ respektiert, Seeding | Umgesetzt + 5 Verhaltenstests |
| 6. Dashboard-Entlastung | 4 Karten, Timer-Filter ≥ 80 %, Limits 6/8, Zähler in Titeln | Umgesetzt |
| 7. Vorschlagsliste | kompakte Hinweisspalte, Tooltip, Score-Ampel | Umgesetzt |
| 8. Regeln & Einstellungen | Erklärpanel, Stufenfilter, übersetzte Labels, neue Settings-Seite | Umgesetzt |
| 9. i18n | 25 neue Keys × 3, alle 5 Audits | OK, 1999 Keys × 3 |
| 10. Tests/Regression | Suite headless | 162 passed, 1 bekannter Sandbox-Fail |

## Umgesetzte Punkte im Detail

### 1. Bilder und Dimensionen: Hersteller zuerst
`logic/pen_dimensions_service.py` erhält ein Hersteller-Verzeichnis (~30 etablierte Marken) mit token-basiertem Längster-Treffer-Matching („Graf von Faber-Castell“ ≠ „Faber-Castell“). Beide URL-Builder stellen eine `site:<hersteller>`-Suche voran; der Online-Lookup läuft zweiphasig und lädt in Phase 1 ausschließlich Links der Hersteller-Domain (Quelle `hersteller:<domain>`). Erst ohne Herstellertreffer folgt das offene Netz. Da Domains offline nicht verifizierbar sind, gibt es das Nutzer-Overlay `manufacturer_domains.json` im Datenverzeichnis – falsche oder fehlende Einträge kosten nichts, weil Stufe 2 immer weiterläuft. Das Pen-Widget reicht das Datenverzeichnis jetzt auch bei der Bildersuche durch.

### 2. Befüllroutine: jede Runde neue Tinten
`get_suggestions(..., avoid_ink_ids=...)` meidet Tinten früherer Runden; das Rotations-Widget führt die Menge über die Sitzung fort. Feste Paarungen 💍 sind vom Meiden ausgenommen. Ist der Pool eines Füllers erschöpft, fällt genau dieser Füller automatisch auf eine neue Runde zurück (Hinweis 🔁) statt leer auszugehen.

### 3. 100 % Zufallsmodus
Neues Setting `rotation_random_mode` (geseedet, Standard aus) plus Einstellungsseite **„Rotation & Vorschläge“**. Aktiv würfelt die Engine pro Füller aus allen Kandidaten – ausgenommen Kombinationen mit blockierender harter Regel (füllerschädigend, z. B. Vac + Shimmer). Feste Paarungen und Pflicht-Füller bleiben respektiert; jede Tinte/jeder Füller max. 1×. Das bisher unsichtbare DB-Setting `rotation_allow_active_ink_duplicates` ist auf derselben Seite jetzt schaltbar.

### 4. Dashboard entschlackt
Vier Karten statt sieben; Bestand/Service/Archiv als kompakte Zeile mit Tooltips. Der Safety-Timer ist jetzt Alarmzentrale statt Inventarliste: nur überfällig oder ≥ 80 % der Maximaltage, Zähler im Titel. Advisor 12→6, Aktivität 20→8 Einträge, Service-Titel mit Zähler. Die „Alles im grünen Bereich“-Logik und das Ausblenden leerer Sektionen bleiben unverändert.

### 5. Tintenvorschläge lesbar
Die Hinweisspalte zeigte bisher einen einzigen Riesenstring aus allen Warnungen und ~10 Hinweisen. Neu: Regelwarnungen vollständig + maximal 2 Hinweise, Rest als „… +N Details“; Volltext im Tooltip und unverändert im Score-Dialog. Score-Ampel: grün ≥ 100, orange < 0, rot bei blockierender Regel. Aktiver Zufallsmodus wird in der Zusammenfassung ausgewiesen.

### 6. Regelseite klarer
Klartext-Erklärpanel über der Regelliste (hart = Schutz/blockierbar, weich = Empfehlung, Warnstufen-Legende, Override-Prinzip). Neuer Warnstufen-Filter. Typ und Warnstufe erscheinen als übersetzte Labels mit Icon statt roher Codes.

### 7. Behobener Fund: i18n-Leak in der Regelliste
„Ja“/„Nein“/„Nein (Gruppe aus)“ in der Wirksam-Spalte waren hartkodiert und liefen an der Übersetzung vorbei (in EN/FR sichtbar deutsch). Jetzt echte Keys `rules.effective_*`; ein statischer Guard verhindert die Wiedereinführung.

## Neu/geändert – Dateien

- `logic/pen_dimensions_service.py` (Herstellerverzeichnis, Overlay, 2-Phasen-Lookup, URL-Builder)
- `logic/rotation_engine.py` (avoid_ink_ids, Zufallsmodus, has_blocked)
- `database/db.py` (Seeding `rotation_random_mode`)
- `ui/rotation_widget.py` (Reroll-Gedächtnis, kompakte Hinweisspalte, Score-Ampel)
- `ui/settings_widget.py` (Seite „Rotation & Vorschläge“, Laden/Speichern)
- `ui/dashboard_widget.py` (4 Karten, Bestandszeile, Timer-Filter, Limits, Titelzähler)
- `ui/rules_widget.py` (Erklärpanel, Stufenfilter, Label-Helfer, Leak-Fix)
- `ui/pen_widget.py` (Overlay-Anbindung Bildersuche)
- `i18n/de.json`, `i18n/en.json`, `i18n/fr.json` (25 neue Keys)
- `tests/test_rotation_random_and_reroll_0279.py` (neu, 18 Tests)
- `tests/test_pen_dimensions_service.py` (+6 Tests)
- Version/Doku: `app_info.py`, `version.json`, `VERSION_INFO.txt`, `README.md`, `latest.json.template`, `docs/latest.json.template`, `installer/FountainPenManager_Setup.iss`, `updater/generate_manifest.py`, `docs/WINDOWS_RELEASE_{DE,EN,FR}.md`, versionsgepinnte Testdateien
- `CHANGELOG_0.2.79_MANUFACTURER_FIRST_ROTATION_UX.md` (neu)

## Validierung

```text
python3 -m compileall -q .                 OK
python3 tools/sync_version.py --check      Alle Versionsdateien synchron: 0.2.79
python3 tools/i18n_audit.py                OK (1999 Keys × 3 Sprachen)
python3 tools/i18n_quality_audit.py        OK (0 untranslated, 0 leakage)
python3 tools/i18n_runtime_audit.py        OK
python3 tools/i18n_key_wiring_audit.py     OK
python3 tools/i18n_visible_text_audit.py   OK (echtes translate_source_text)
Tests (headless Shim)                      162 passed, 1 failed*
python3 dev_check.py                       Syntax OK (Pycache vor Paketierung bereinigt)
```

\* Der eine Fail ist `test_logic_migration_hardening.py`: benötigt echtes SQLAlchemy, das in der netzlosen Sandbox nicht installierbar ist. Kein Code-Defekt; auf einem System mit installierten Abhängigkeiten läuft der Test.

## Ehrliche Einschränkungen

- **Kein GUI-Smoke-Test möglich** (PySide6 nicht in der Sandbox): Die UI-Änderungen an Dashboard, Rotation, Regeln und Einstellungen sind syntaktisch und statisch geprüft, aber nicht am Bildschirm verifiziert. Vor Veröffentlichung bitte manuell prüfen: Einstellungsseite „Rotation & Vorschläge“ öffnen/speichern, zweimal „💡 Vorschläge“ klicken (andere Tinten?), Zufallsmodus einschalten und Vorschläge prüfen, Dashboard-Ansicht, Regelliste mit Stufenfilter.
- **Hersteller-Domains nicht online verifiziert** (kein Netz in der Sandbox). Die Liste enthält nur etablierte Domains; Fehleinträge degradieren sanft zur Web-Phase und sind per `manufacturer_domains.json` korrigierbar.
- Zufälligkeit ist nicht seedbar konfiguriert (bewusst: echter Zufall pro Klick).
- Kein Windows-Build/Installer-Test in dieser Umgebung.

## Release-Urteil

**Freigabe empfohlen für v0.2.79 Source/Portable RC** – vorbehaltlich des manuellen GUI-Smoke-Tests (Checkliste oben).
