# KILLCRITIC Audit – FountainPen Manager v0.2.74 → v0.2.75

## Ziel

Vergleich und Tiefenanalyse der hochgeladenen v0.2.74 gegen die zuvor gelieferte v0.2.72 mit Fokus auf Releasefähigkeit, Usability, UI-Konsistenz und DAU-freundliche Bedienung.

## Kurzurteil

- v0.2.74 war funktional deutlich reifer als v0.2.72 und enthielt sinnvolle UI-/I18N-Härtung.
- v0.2.74 war als Source-/Portable-RC fast freigabefähig.
- Zwei reale Release-Schwächen wurden gefunden und in v0.2.75 behoben:
  1. README verwies auf nicht vorhandene v0.2.74-Release-Dateien.
  2. `logic/event_bus.py` hatte eine harte PySide6-Abhängigkeit, obwohl `logic/rotation_engine.py` ihn importiert. Das ist im GUI-Betrieb okay, aber für Headless-Logik-/CI-Audits unnötig fragil.

## Ergebnis nach Härtung

**v0.2.75 ist als Source-/Portable-RC releasefähig.**

Für den öffentlichen Final Release bleibt nur der echte manuelle GUI-Smoke-Test auf Linux/Windows mit installierter PySide6-Umgebung offen.

## Automatische Validierung

```text
python -m compileall -q .                    OK
python tools/sync_version.py --check          Alle Versionsdateien synchron: 0.2.75
python -m pytest -q -ra                       133 passed
python tools/i18n_audit.py                    OK – 1955 Keys × 3 Sprachen
python tools/i18n_quality_audit.py            OK
python tools/i18n_runtime_audit.py            OK
python tools/i18n_key_wiring_audit.py         OK
python tools/i18n_visible_text_audit.py       OK
python tools/gui_smoke_test.py                SKIP: PySide6/runtime package missing: PySide6
```

## Vergleich v0.2.72 → v0.2.74

Geändert gegenüber v0.2.72:

- Version und Release-Dokumente auf v0.2.74 angehoben.
- Füller-Widget: harte deutsche Status-/Service-Texte wurden besser übersetzt.
- Rotation: harter-Regel-Suffix nutzt jetzt `rotation.warning_hard_rule_suffix` statt deutschem Literal.
- Zusätzlicher Guard-Test gegen erneute i18n-Leaks im Füller-/Rotation-Kontext.
- Audit-Dokumente v0.2.73/v0.2.74 ergänzt.

Bewertung: Die funktionalen Codeänderungen sind klein, aber sinnvoll. Die Version ist keine große Feature-Version, sondern ein Release-/UI-Härtungsstand.

## Gefundene reale Probleme in v0.2.74

### 1. README-Dateiverweise waren kaputt

README verwies auf:

```text
CHANGELOG_0.2.74_GITHUB_RELEASE_URL_FINALIZATION.md
RELEASE_REPORT_v0.2.74_GITHUB_RELEASE_URL_FINALIZATION.md
```

Diese Dateien existierten im Paket nicht. Für Entwickler auffindbar, für normale Nutzer aber ein Vertrauensbruch: Doku sagt „hier ist der Report“, Datei fehlt.

**Fix in v0.2.75:** README verweist jetzt auf vorhandene v0.2.75-Dateien. Regressionstest prüft, dass alle README-`.md`-Referenzen wirklich existieren.

### 2. EventBus war nicht headless-robust

`logic/rotation_engine.py` importiert `logic.event_bus`. `logic.event_bus` importierte PySide6 direkt. Ohne PySide6 konnte damit ein Logikimport scheitern, obwohl keine GUI gestartet wird.

**Fix in v0.2.75:** Minimaler Headless-Fallback für `QObject`/`Signal` ergänzt. Im echten GUI-Betrieb nutzt die App weiterhin PySide6. In Headless-Tests funktionieren Import und einfache Signal-Emission ohne Qt.

## 200-Loop-KILLCRITIC Matrix

Die 200 Loops sind als 20 Themen × 10 Prüfpunkte abgebildet.

| Thema | 10er-Loop Ergebnis | Urteil |
|---|---:|---|
| 1. Versionskonsistenz | 10/10 nach Fix | OK |
| 2. Release-Dokumentation | 8/10 in v0.2.74, 10/10 in v0.2.75 | Gefixt |
| 3. GitHub-/Updater-URL | 10/10 | OK |
| 4. Manifest-Templates | 10/10 | OK, SHA256 bleibt Build-Platzhalter |
| 5. Windows-Doku | 10/10 | OK |
| 6. Paket-Hygiene | 10/10 | OK, keine Caches im ZIP |
| 7. Testsuite | 10/10 | OK |
| 8. Headless-Testbarkeit | 7/10 in v0.2.74, 10/10 in v0.2.75 | Gefixt |
| 9. I18N-Key-Parität | 10/10 | OK |
| 10. Runtime-I18N | 10/10 | OK |
| 11. Deutsche UI-Leaks | 10/10 | OK nach v0.2.74-Fix |
| 12. Navigation/DAU-Struktur | 8/10 | Gut, aber noch nicht perfekt |
| 13. Dashboard-Klarheit | 8/10 | Gut, aber Informationsdichte bleibt hoch |
| 14. Dialog-Struktur | 9/10 | Gut: Tabs/Scrollbereiche vorhanden |
| 15. Warnstufen/Regellogik | 9/10 | Gut, Override bleibt manuell möglich |
| 16. Rotation/Override | 9/10 | Gut, harte Regeln transparent |
| 17. Suche/Shortcuts | 8/10 | Gut, aber Suche ist seitenbezogen, nicht wirklich global |
| 18. Fehler-/Fallback-Verhalten | 8/10 | Besser nach EventBus-Fix; viele `except Exception` bleiben weich |
| 19. Build-/CI-Readiness | 8/10 | Gut, echter Windows-Build noch erforderlich |
| 20. Final-Release-Risiko | 8/10 | RC ja; Final nach GUI-Smoke-Test |

## UI-/Usability-Kritik

Die UI ist nicht mehr chaotisch, aber noch nicht maximal DAU-freundlich.

Stärken:

- Seitenleiste ist gruppiert.
- Hauptmodule sind per Shortcut erreichbar.
- Dashboard hat Kontextaktionen.
- Füller-Dialog ist in sinnvolle Bereiche aufgeteilt.
- Warnlogik wirkt weniger bevormundend, weil Override möglich bleibt.

Schwächen:

- 14 Module bleiben viel für Erstnutzer.
- Dashboard ist weiterhin eher Power-User-lastig.
- Globale Suche filtert nur die aktive Seite; der Name „global“ ist technisch intern, nicht Nutzerlogik.
- Viele Aktionen sind vorhanden, aber nicht immer als geführter Workflow sichtbar.
- Echter GUI-Test fehlt weiter, dadurch keine finale Aussage zu Layout-Brüchen, Fokus-Reihenfolge, Dialoggrößen und Windows-Rendering.

## Release-Entscheidung

| Ziel | Urteil |
|---|---|
| Source-/Portable-RC | Freigabe möglich |
| Öffentlicher Final Release | Nach manuellem GUI-Smoke-Test |
| Windows-Installer | Nach echtem Build + Installationstest |
| Updater | URL korrekt, aber erst mit realem `latest.json` + SHA256 final |

## Empfohlener nächster UI-Schritt

Nicht noch mehr Funktionen einbauen. Der nächste harte UI-Schritt sollte ein echter **Einfachmodus** sein:

1. Start: „Füller eintragen“, „Tinte eintragen“, „Füller befüllen“, „Reinigen“.
2. Sammlung: nur Füller/Tinte/Papier.
3. Experte: Regeln, Statistik, Sammler-Lab, Budget-Brücke.
4. Jede Seite bekommt oben eine Kurzantwort: „Was mache ich hier?“.
5. Pro Seite maximal eine dominante Primäraktion.

## Fazit

v0.2.74 war gut, aber nicht sauber genug für einen öffentlichen Release, weil Release-Doku und Headless-Logikrobustheit Lücken hatten. v0.2.75 behebt diese Punkte ohne riskante UI-Umbauten.
