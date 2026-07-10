# Release Report – FountainPen Manager v0.2.85 VISUAL SIZE + SEARCH CASCADE

## Ergebnis
**Status: Releasefähig als Source-/Portable-Kandidat (RC).**

Diese Runde (a) behebt den gemeldeten Praxisfehler „Suche/Dimensionen funktionieren nicht" an der Wurzel und (b) integriert den Parallelzweig `v0.2.84 VISUAL_SIZE_AI_SEARCH`.

## Vergleichs- und Merge-Matrix

| Thema | Sieger | Begründung |
|---|---|---|
| Größenvergleich | **0.2.84-Zweig** | Vollständig, sinnvoll (Überlagert/Zeilen, 4 Metriken, Lineal); überspringt Füller ohne Messwert statt zu raten |
| Media-Ablage | **0.2.84-Zweig** | Sauberer Service mit 15-MB-Cap und `is_inside`-Pfadschutz; Backup-freundlich |
| Google-KI-Suchstufe | **0.2.84-Zweig** | Guter Zusatz; degradiert sauber zu normaler Suche, wenn `udm=50` nicht verfügbar |
| Manuelle Suche | **Merge** | Zweig entfernte `site:` komplett → Anforderung „erst Hersteller" verletzt. Jetzt Kaskade: Hersteller → KI → Web |
| Automatischer Lookup | **Mein Fix** | Zweig hatte Voll-Phrase **plus Exact-Phrase-Quoting** in der `site:`-Phase → treffer-unmöglich; jetzt Minimal-Query |
| HTML-Endpunkt | **Mein Fix** | `html.duckduckgo.com/html/` ist stabiler |
| Audit-Tool | **Mein Stand** | Funktionaler Superset (Zweig unterschied sich nur in Versionsstrings); um 8 Feature-Invarianten erweitert |

## Diagnose des Meldefalls (Screenshot)
Geöffnete URL enthielt `site:faber-castell.com` **plus 10 Pflichtwörter**. Suchmaschinen verlangen alle Begriffe gleichzeitig → auf einer Herstellerseite strukturell null Treffer. Der **Parser** wurde ausdrücklich entlastet: Deutsche Herstellerangaben („Länge geschlossen: 14,4 cm") werden korrekt zu 144 mm konvertiert (Konfidenz 0.91), Füllsystem-Deutsch (kolben/patrone/konverter) ist abgedeckt. Der Fehler lag allein in den Queries.

**Root-Cause ehrlich benannt:** Merge-Regression aus v0.2.80, entstanden durch meine eigene Fehleinschätzung im damaligen Merge-Report („inhaltlich gleich").

## Wirkung, verifiziert
```
dim[0]  https://www.google.com/search?q=site%3Afaber-castell.com+Essetio
img[0]  https://www.google.com/search?q=site%3Afaber-castell.com+Essetio&tbm=isch
auto[0] https://html.duckduckgo.com/html/?q=site%3Afaber-castell.com+Essetio
dim[1]  Google-KI-Prompt (udm=50), dim[2]/dim[3] klassische Web-Suche
```

## Validierung
```text
compileall / sync_version --check            OK · 0.2.85 synchron
i18n-Audits (5)                              OK (2043 Keys × 3)
killcritic_1000_loop_audit                   OK (69 × 20 = 1380, 0 Findings)
Tests (headless Shim)                        190 passed, 1 failed*
```
\* Bekannter Sandbox-Fail (`test_logic_migration_hardening.py`, SQLAlchemy nicht installierbar). Kein Code-Defekt.

## Bewusste Abweichung vom Zweig – zur Kenntnisnahme
Der 0.2.84-Zweig wollte die manuelle Suche breit und ohne `site:`. Ich habe die Herstellerstufe **wiederhergestellt**, weil das eine ausdrückliche Anforderung war, und den eigentlichen Bug stattdessen behoben. Der Zweig-Test, der „kein `site:`" festschrieb, wurde durch einen Kaskaden-Test ersetzt. Falls die breite Suche als erste Stufe gewünscht ist, ist das eine Zeile Reihenfolge – bitte sagen.

## Ehrliche Einschränkungen
- **Kein GUI-Smoke-Test möglich** (PySide6 fehlt in der Sandbox). Der Größenvergleich und der Media-Import sind statisch/über Unit-Tests geprüft, aber nicht am Bildschirm.
- Ob DuckDuckGo dem automatischen Lookup im echten Netz HTML ohne Bot-Hürde liefert, ist aus der Sandbox nicht prüfbar. Der Query-Fix behebt die sichere, reproduzierbare Ursache; die **manuellen** Browser-Suchen treffen in jedem Fall.
- `udm=50` ist ein Google-internes Flag ohne Zusage; bei Nichtverfügbarkeit öffnet Google normal – bewusst so gebaut.

## Praxis-Checkliste
1. Füller-Dialog → Faber-Castell / Essetio → „Maße suchen": Erster Treffer-Tab muss Essetio auf faber-castell.com zeigen.
2. „Bilder suchen": Tab 1 Herstellerbilder, Tab 2 KI-Prompt, Tab 3 offene Bildersuche.
3. Größenvergleich mit ≥ 2 Füllern mit gepflegten Maßen: Überlagert- und Zeilen-Modus, alle 4 Metriken.
4. Schreibprobe mit Bild anlegen → Datei muss unter `media/` im Datenverzeichnis landen.
5. Automatischer Lookup: falls weiterhin „Kein sicherer Treffer" bei bestehender Verbindung → melden; dann baue ich einen Diagnose-Log-Schalter ein.

## Release-Urteil
**Freigabe empfohlen für v0.2.85 Source/Portable RC** – vorbehaltlich des manuellen GUI-/Praxis-Checks.
