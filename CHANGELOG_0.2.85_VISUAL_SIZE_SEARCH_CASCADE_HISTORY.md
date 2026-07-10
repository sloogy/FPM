# Changelog v0.2.85 – VISUAL SIZE + SEARCH CASCADE (Merge mit 0.2.84-Zweig)

Vereinigt meinen Query-Fix-Stand mit dem Parallelzweig `v0.2.84 VISUAL_SIZE_AI_SEARCH`. Pro Thema die bessere Lösung, ohne Features zu verlieren.

## Übernommen aus dem 0.2.84-Zweig
- **Visueller Größenvergleich** (`ui/pen_widget.py`): stilisierte Silhouetten, Modi *Überlagert* / *Zeilen*, Metriken *Beste verfügbare / Geschlossen / Ohne Kappe / Aufgesteckt*, Lineal und Farbcodierung. Füller ohne passenden Messwert werden übersprungen statt geraten.
- **`logic/media_storage_service.py`** (neu): strukturierte Medienablage unter `media/<pen-slug>/…` im Datenverzeichnis, 15-MB-Obergrenze, Pfad-Ausbruch-Schutz (`is_inside`), eindeutige Dateinamen, Download-Helfer. Plus `tests/test_media_storage_service.py`.
- **Media-Import in Schreibproben** (`ui/writing_samples_widget.py`) und Bild-Übernahme im Füller-Dialog.
- **DB-Hygiene**: verwaiste Medienordner werden aufgeräumt.
- **Google-KI-Suchstufe**: natürlichsprachiger Prompt mit `udm=50`; fällt automatisch auf normale Google-Suche zurück, wenn der KI-Modus nicht verfügbar ist.

## Korrigiert gegenüber dem 0.2.84-Zweig
### 1. Hersteller-zuerst wiederhergestellt (Anforderung)
Der Zweig hatte `site:` **aus der manuellen Suche entfernt**, um den Nulltreffer-Bug zu umgehen. Damit war die ausdrückliche Anforderung „Bilder erst bei den Herstellern / Dimensionen erst Hersteller, dann im Netz" nicht mehr erfüllt. Die Ursache war aber nie die `site:`-Einschränkung, sondern die **überladene Query**.

**Jetzt: dreistufige Kaskade** in beiden manuellen Suchen:
1. Hersteller-Domain(s), `site:<domain> <Modell>` – minimal formuliert,
2. Google-KI-Prompt (`udm=50`, aus dem Zweig),
3. klassische Google-/DuckDuckGo-Suche als Rückfallebene.

Bei unbekannten Marken entfällt Stufe 1; die KI-Stufe führt.

### 2. Automatischer Lookup: Bug war dort **nicht** behoben, sondern verschärft
Der Zweig ließ im Parser-Pfad (`build_online_dimension_search_urls`, `_phase_plan`) die volle Query in der `site:`-Phase – inzwischen sogar mit **Exact-Phrase-Quoting** (`site:faber-castell.com "Faber-Castell Essetio" fountain pen dimensions length weight ink capacity filling system`). Das ist strukturell treffer-unmöglich. Jetzt auch hier Minimal-Query.

### 3. Stabilerer HTML-Endpunkt
Automatischer Lookup nutzt `html.duckduckgo.com/html/` statt `duckduckgo.com/html/`.

## Root-Cause (unverändert gültig)
Merge-Regression aus v0.2.80: Der 0.2.79A-Stand nutzte in der `site:`-Phase bewusst nur den Modellnamen; beim Zweig-Merge wurde die B-Builder-Struktur mit Voll-Phrase übernommen (damals von mir als „inhaltlich gleich" fehleingeschätzt). Suchmaschinen verlangen alle Wörter gleichzeitig → auf einer Herstellerseite null Treffer. Gemeldeter Fall: Faber-Castell Essetio.

## Absicherung
- Ersetzter Zweig-Test `test_manual_browser_search_is_ai_friendly_without_site_restriction` → **`test_manual_browser_search_is_manufacturer_first_then_ai_then_web`**: prüft die Kaskade, verbietet Voll-Phrase/Quoting in jeder `site:`-URL, verlangt die KI-Stufe und die offene Rückfallebene.
- Neu: `test_site_queries_are_minimal_regression_essetio` (exakter Meldefall, alle drei Pfade), `test_site_query_falls_back_to_brand_without_model`.
- Zwei Alt-Tests indexunabhängig gemacht (Marken mit mehreren Domains, z. B. Pilot EU/US).
- KILLCRITIC-Audit: +8 Invarianten (Kaskade hersteller-zuerst, KI-Stufe, Bild-Kaskade, Media-Service inkl. Size-Cap und Pfad-Guard, Größenvergleich-Modi/Metriken) → **69 × 20 = 1380 Checks**.

## Dokumentation
- Handbuch: Kap. 17.2/17.3 auf die Kaskade umgeschrieben; **neu Kap. 6.6 Visueller Größenvergleich** und **6.7 Verwaltete Medien**.
- Zweig-Historie (`CHANGELOG/RELEASE_REPORT` 0.2.83/0.2.84 des Parallelzweigs) liegt bei.
