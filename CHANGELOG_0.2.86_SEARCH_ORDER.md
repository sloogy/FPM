# Changelog v0.2.86 – SEARCH ORDER (KI bei Maßen, Hersteller bei Bildern)

## Umgesetzte Vorgabe
- **Maße:** KI-Stufe zuerst.
- **Bilder:** Hersteller-Stufe zuerst.

Die Reihenfolge ist damit bewusst **asymmetrisch** – weil sich die Ziele unterscheiden: Bei Zahlen gewinnt die KI-Übersicht (trägt Werte aus mehreren Quellen zusammen und nennt sie); bei Produktfotos gewinnt die offizielle Herstellerquelle (korrekte Farbe, Finish, aktuelle Ausführung).

## Neue Reihenfolgen

**`build_dimension_search_urls` (Maße):**
1. Google-KI-Prompt (`udm=50`, natürlichsprachig)
2. Hersteller-Domain(s), `site:<domain> <Modell>` – minimal formuliert
3. Google-Websuche, danach DuckDuckGo (Rückfallebene)

**`build_image_search_urls` (Bilder):**
1. Hersteller-Domain(s) als Bildersuche (`tbm=isch`), minimal formuliert
2. Google-KI-Prompt
3. Google Images, danach DuckDuckGo-Bilder

**Unverändert:** Der automatische Parser-Lookup (`build_online_dimension_search_urls`, `_phase_plan`) bleibt hersteller-zuerst. Dort gibt es keine KI-Übersicht – der Parser liest Seiten selbst. Ohne Hersteller-Treffer folgt wie bisher die offene Netzphase.

**Ebenfalls unverändert:** `site:`-Stufen tragen nur den Modellnamen (Marke ist durch die Domain gegeben). Der Nulltreffer-Bug aus dem Meldefall Faber-Castell Essetio bleibt behoben. Bei unbekannten Marken entfällt die Hersteller-Stufe; dann führt in beiden Suchen die KI-Stufe.

## Absicherung
- Test `test_dimension_search_is_ai_first_images_are_manufacturer_first` prüft beide Reihenfolgen positionsgenau (inkl. Marken mit mehreren Domains wie Pilot EU/US), verbietet weiterhin Voll-Phrase und Exact-Phrase-Quoting in jeder `site:`-URL und verlangt die offene Rückfallebene in beiden Suchen.
- Regressions-Guard Essetio an die neuen Indizes angepasst: `dim[0]` KI, `dim[1]` Hersteller, `img[0]` Hersteller.
- KILLCRITIC-Audit: neuer quelltextnaher Reihenfolge-Guard `_order_ok()` → `dim_search_ai_first`, `img_search_manufacturer_first`, `auto_lookup_manufacturer_first`. **70 × 20 = 1400 Checks, 0 Findings.** Der Guard wurde gegen den Fehlerfall geprüft: vertauschte Reihenfolge liefert nachweislich `False` (nicht nur „grün, weil vorhanden").

## Dokumentation
- Handbuch Kap. 17.3 zeigt beide Kaskaden getrennt, begründet die Asymmetrie und weist darauf hin, dass der automatische Lookup davon unberührt bleibt. Querverweis in Kap. 6.4 ergänzt.
