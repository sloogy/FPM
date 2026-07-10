# Changelog v0.2.81 – USABILITY & HELP HARDENING

## Ausgangspunkt: Usability-Analyse aus Neuling-Sicht
Auftrag: „Ist es logisch für einen neuen User? Ist es übersichtlich? Ist das Wiki gründlich?" Befund: Die App-Oberfläche ist nach 0.2.80 gut erklärt (Regel-Overview, Settings-Noten, Onboarding, Tour-Karte), aber die **In-App-Hilfe hinkte zwei Versionen hinterher**: Der Kern-Workflow (Vorschläge/Reroll/Zufall) und die komplette Hersteller-Recherche inkl. Overlay waren nirgends dokumentiert; das Glossar kannte 6 Begriffe, aber weder EDC noch 💍/⭐ noch hart/weich.

## Neu: Hilfe-Tab „Rotation & Vorschläge" (Position 2, direkt nach Schnellstart)
Fünf Karten: (1) Workflow – Slots, Papier/Thema, Klick auf Zeile = Befüllen, was automatisch ausgelassen wird; (2) Score & Hinweise – Ampelfarben, „… +N", Warum-Klick auf den Score; (3) Reroll – nochmal klicken = andere Paare, 🔁-Rundenneustart; (4) 🎲 Zufall dosieren – 0–100 %, Sicherheitsgrenze (blockierende Regeln + Full-Auto-Rejects nie), Verweis auf Einstellungen; (5) 💍/⭐ – feste Paarung vs. Pflicht-Füller, Override-Grundsatz.

## Neu: Hilfe-Tab „Recherche & Daten" (vor dem Glossar)
Drei Karten: (1) Hersteller zuerst – Ablauf der Maße-/Bildersuche, konservative Übernahme nur in leere Felder, lokaler Cache; (2) Quellen-Labels – `manufacturer:` / `online:` / `cache` erklärt; (3) **Overlay `manufacturer_domains.json` erstmals dokumentiert**, mit kopierbarem JSON-Beispiel (String- und Listen-Variante). Ohne dieses Kapitel war das Power-Feature praktisch unauffindbar.

## Schnellstart & Dashboard
- Quickstart um **Schritt 5** ergänzt: von „Daten anlegen" zum eigentlichen Nutzen („💡 Vorschläge" → Klick auf Zeile).
- Neue Karte **„Das Dashboard lesen"**: die 4 Karten, die Bestandszeile, und die wichtige Erwartungskorrektur, dass der Safety-Timer bewusst nur Fälliges/bald Fälliges zeigt (Rest unter „Aktuelle Belegung").

## Glossar 6 → 12
Neu: EDC, Vac/Vacuum (mit Begründung der Shimmer-Regel), 💍 Feste Paarung, ⭐ Pflicht-Füller, Harte/weiche Regel, Reroll.

## Mikro-Usability
- **Tooltip am „💡 Vorschläge"-Button** (`rotation.generate_tooltip`): erklärt das Reroll-Verhalten am Ort des Geschehens.
- Hilfe-Untertitel erweitert: Regeln **+ Vorschläge + Recherche** statt nur Regel-Engine.

## Absicherung
- Neuer statischer Guard `tests/test_help_coverage_0281_static.py` (8 Tests): Tabs registriert und richtig einsortiert, alle Keys ×3 Sprachen vorhanden und substanziell (> 120 Zeichen je Karte), Rotation-Kapitel erwähnt 💍/⭐/🔁/Zufall/Score, Overlay-Doku enthält Dateiname + Listen-Beispiel, Quickstart endet mit Schritt 5, Glossar vollständig, Tooltip verdrahtet, JSON-Beispiel bleibt formatierungssicher (t() ohne kwargs).
- KILLCRITIC-Audit: +4 Hilfe-Invarianten → 54 × 20 = 1080 Checks, 0 Findings.

## Technik
- 31 neue i18n-Keys × 3 Sprachen (jetzt 2029 × 3, Parität grün); 1 Bestandstext (Hilfe-Untertitel) in 3 Sprachen präzisiert; `help.quickstart_body` in 3 Sprachen erweitert.
- Keine Logikänderungen an Engine/Datenbank – reine Doku-, Text- und Tooltip-Runde plus Guards.
