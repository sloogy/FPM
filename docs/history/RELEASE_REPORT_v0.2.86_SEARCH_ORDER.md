# Release Report – FountainPen Manager v0.2.86 SEARCH ORDER

## Ergebnis
**Status: Releasefähig als Source-/Portable-Kandidat (RC).**

Kleine, gezielte Runde: die Suchreihenfolgen nach Vorgabe umgestellt – Maße KI-zuerst, Bilder hersteller-zuerst.

## Was geändert wurde
| Suche | Stufe 1 | Stufe 2 | Stufe 3 |
|---|---|---|---|
| **Maße** | Google-KI-Prompt (`udm=50`) | Hersteller-Domain(s) `site:<domain> <Modell>` | Google-Web → DuckDuckGo |
| **Bilder** | Hersteller-Bildersuche `site:… &tbm=isch` | Google-KI-Prompt | Google Images → DuckDuckGo |
| **Auto-Lookup (Parser)** | Hersteller-Domain(s) | – | offene Netzphase |

Verifiziert am Meldefall Faber-Castell Essetio:
```
dim[0] …/search?q=%22Faber-Castell+Essetio%22+fountain+pen+dimensions… (udm=50)
dim[1] …/search?q=site%3Afaber-castell.com+Essetio
img[0] …/search?q=site%3Afaber-castell.com+Essetio&tbm=isch
auto[0] https://html.duckduckgo.com/html/?q=site%3Afaber-castell.com+Essetio
```

## Bewusste Entscheidungen (zur Kenntnisnahme)
1. **Die Hersteller-Stufe bleibt bei den Maßen erhalten** – nur eine Position nach hinten. Die KI kann ungenau sein oder Quellen weglassen; die Herstellerseite ist die belastbare Primärquelle und ist jetzt genau einen Tab entfernt. Falls sie bei Maßen ganz entfallen soll, ist das eine Zeile – bitte sagen.
2. **Der automatische Parser-Lookup bleibt hersteller-zuerst.** Er liest Seiten selbst; eine KI-Übersicht gibt es dort nicht zu holen. Ihn auf die KI-Seite zu schicken, brächte nur unstrukturiertes HTML.

## Absicherung
- Positionsgenauer Reihenfolge-Test (robust gegen Marken mit mehreren Domains).
- Neuer KILLCRITIC-Guard `_order_ok()`: prüft quelltextnah, dass `ai_mode=True` bei Maßen **vor** und bei Bildern **nach** der `manufacturer_domains_for_brand`-Schleife steht. **Wirksamkeit belegt:** mit vertauschtem Parameter liefert der Guard `False` – er ist diskriminierend, nicht bloß „vorhanden“.
- Alle `site:`-URLs bleiben frei von Voll-Phrase und Exact-Phrase-Quoting (Regressions-Guard Essetio).

## Validierung
```text
compileall / sync_version --check            OK · 0.2.86 synchron
i18n-Audits (5)                              OK (2043 Keys × 3)
killcritic_1000_loop_audit                   OK (70 × 20 = 1400, 0 Findings)
Tests (headless Shim)                        190 passed, 1 failed*
```
\* Bekannter Sandbox-Fail (`test_logic_migration_hardening.py`, SQLAlchemy nicht installierbar). Kein Code-Defekt.

## Ehrliche Einschränkungen
- **Kein GUI-Smoke-Test möglich** (PySide6 fehlt in der Sandbox). Die URL-Kaskaden sind per Unit-Test verifiziert, das Öffnen im Browser nicht.
- `udm=50` ist ein nicht zugesichertes Google-Flag. Ist der KI-Modus für Konto/Region nicht verfügbar, öffnet Google eine normale Suche mit demselben Prompt – die Stufe bleibt nützlich, aber es gibt keine Garantie auf die KI-Übersicht.
- Ob die KI-Übersicht für ein konkretes Modell tatsächlich Maße liefert, ist von außen nicht prüfbar; die Hersteller-Stufe direkt dahinter ist genau dafür die Absicherung.

## Praxis-Checkliste
1. Füller-Dialog → „Maße suchen“: Erster Tab = Google mit KI-Prompt; zweiter Tab = `site:hersteller.com <Modell>`.
2. „Bilder suchen“: Erster Tab = Herstellerbilder; danach KI-Prompt; danach offene Bildersuche.
3. Unbekannte Marke (z. B. Eigenbau): beide Suchen starten mit dem KI-Prompt, keine site:-Stufe.

## Release-Urteil
**Freigabe empfohlen für v0.2.86 Source/Portable RC** – vorbehaltlich des manuellen Praxis-Checks.
