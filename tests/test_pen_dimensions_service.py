from logic.pen_dimensions_service import (
    PenDimensionSuggestion,
    build_dimension_search_urls,
    build_image_search_urls,
    lookup_pen_dimensions,
    match_cached_dimensions,
    normalize_fill_system,
    normalize_pen_key,
    save_dimension_cache,
)


def test_normalize_pen_key_is_stable_for_umlauts_and_punctuation():
    assert normalize_pen_key("Pelikan", "M-1000 Grün") == "pelikan m 1000 grun"


def test_cached_dimensions_exact_match_wins():
    cache = [
        PenDimensionSuggestion("Pilot", "Custom 74", length_mm=143, weight_g=20, confidence=0.8),
        PenDimensionSuggestion("Pilot", "Custom Heritage 92", length_mm=137, confidence=0.8),
    ]
    matches = match_cached_dimensions("Pilot", "Custom 74", cache)
    assert matches
    assert matches[0].model == "Custom 74"
    assert matches[0].values()["length_mm"] == 143


def test_lookup_uses_user_cache_and_provides_web_urls(tmp_path):
    cache_path = tmp_path / "pen_dimensions_cache.json"
    save_dimension_cache(cache_path, [PenDimensionSuggestion("Lamy", "Safari", length_mm=139, source="manual")])
    result = lookup_pen_dimensions("Lamy", "Safari", cache_path=cache_path)
    assert result.best is not None
    assert result.best.source == "manual"
    assert result.message_code == "cache_match"
    assert result.search_urls


def test_lookup_without_cache_is_manual_online_flow(tmp_path):
    result = lookup_pen_dimensions("Unknown", "Mystery", cache_path=tmp_path / "missing.json")
    assert result.best is None
    assert result.message_code == "manual_online_lookup"
    assert "fountain+pen+dimensions" in result.search_urls[0]


def test_search_urls_are_browser_safe():
    urls = build_dimension_search_urls("Pilot", "Custom 74")
    assert all(u.startswith(("https://www.google.com/search?", "https://duckduckgo.com/?")) for u in urls)
    assert "udm=50" in urls[0]  # Maße: KI-Stufe führt (v0.2.86)
    assert any("site%3A" in u and "Custom" in u for u in urls)  # Hersteller-Stufe folgt
    assert any("site%3A" not in u and "Pilot" in u for u in urls)


def test_cached_reference_data_can_include_fill_system_capacity_and_images(tmp_path):
    cache_path = tmp_path / "pen_dimensions_cache.json"
    save_dimension_cache(
        cache_path,
        [
            PenDimensionSuggestion(
                "Asvine",
                "V200",
                fill_system="vacuum filler",
                ink_capacity_ml=2.2,
                image_urls=("https://example.com/asvine-v200.jpg",),
                confidence=0.9,
            )
        ],
    )
    result = lookup_pen_dimensions("Asvine", "V200", cache_path=cache_path)
    assert result.best is not None
    assert result.best.reference_values()["fill_system"] == "vac"
    assert result.best.reference_values()["ink_capacity_ml"] == 2.2
    assert result.best.reference_values()["image_url"].endswith("asvine-v200.jpg")
    assert result.image_search_urls


def test_fill_system_aliases_are_normalized_for_cache_imports():
    assert normalize_fill_system("Kolben") == "piston"
    assert normalize_fill_system("cartridge/converter") == "converter"
    assert normalize_fill_system("unknown exotic") is None


def test_image_search_urls_are_browser_safe():
    urls = build_image_search_urls("Pelikan", "M1000")
    assert all(u.startswith(("https://www.google.com/search?", "https://duckduckgo.com/?")) for u in urls)
    # Stufe 1 Hersteller-Bilder, danach KI-Prompt, danach offene Bildersuche.
    assert "site%3Apelikan.com" in urls[0] and "tbm=isch" in urls[0]
    assert any("udm=50" in u and "site%3A" not in u for u in urls)
    assert any("tbm=isch" in u and "site%3A" not in u for u in urls)
    assert any("site%3A" not in u and "Pelikan" in u for u in urls)


def test_online_parser_extracts_structured_reference_text():
    from logic.pen_dimensions_service import extract_dimension_suggestion_from_text

    html = """
    <html><body>
      <h1>Pilot Custom 74 Fountain Pen</h1>
      <table>
        <tr><th>Length capped</th><td>143 mm</td></tr>
        <tr><th>Length uncapped</th><td>126 mm</td></tr>
        <tr><th>Length posted</th><td>159 mm</td></tr>
        <tr><th>Max diameter</th><td>14.7 mm</td></tr>
        <tr><th>Section diameter</th><td>10.4 mm</td></tr>
        <tr><th>Weight</th><td>21 g</td></tr>
        <tr><th>Ink capacity</th><td>1.1 ml</td></tr>
        <tr><th>Filling system</th><td>Cartridge/converter</td></tr>
      </table>
    </body></html>
    """
    suggestion = extract_dimension_suggestion_from_text("Pilot", "Custom 74", html, source_url="https://example.test/pilot")
    assert suggestion is not None
    assert suggestion.values()["length_mm"] == 143
    assert suggestion.values()["length_uncapped_mm"] == 126
    assert suggestion.values()["length_posted_mm"] == 159
    assert suggestion.values()["diameter_mm"] == 14.7
    assert suggestion.values()["section_diameter_mm"] == 10.4
    assert suggestion.values()["weight_g"] == 21
    assert suggestion.capacity_values()["ink_capacity_ml"] == 1.1
    assert suggestion.reference_values()["fill_system"] == "converter"
    assert suggestion.confidence >= 0.55


def test_lookup_online_uses_injected_fetcher_without_network(tmp_path):
    html_search = '''
      <a class="result__a" href="https://example.test/lamy-safari">Lamy Safari dimensions</a>
      <div class="result__snippet">Lamy Safari fountain pen specs</div>
    '''
    html_page = '''
      <h1>Lamy Safari Fountain Pen</h1>
      Length capped: 139 mm. Length uncapped: 129 mm. Posted length: 165 mm.
      Diameter: 13 mm. Grip diameter: 10.5 mm. Weight: 17 g. Ink capacity: 1.5 ml.
      Filling system: cartridge/converter.
    '''
    calls = []

    def fetcher(url, timeout_s):
        calls.append(url)
        if "duckduckgo" in url:
            return html_search
        return html_page

    result = lookup_pen_dimensions(
        "Lamy",
        "Safari",
        cache_path=tmp_path / "missing.json",
        allow_online=True,
        fetcher=fetcher,
    )
    assert calls and "duckduckgo" in calls[0]
    assert result.message_code == "online_match"
    assert result.best is not None
    assert result.best.values()["length_mm"] == 139
    assert result.best.reference_values()["fill_system"] == "converter"


def test_lookup_keeps_network_off_unless_requested(tmp_path):
    def fetcher(_url, _timeout_s):
        raise AssertionError("network fetcher must not be called")

    result = lookup_pen_dimensions(
        "Unknown",
        "Mystery",
        cache_path=tmp_path / "missing.json",
        fetcher=fetcher,
    )
    assert result.best is None
    assert result.message_code == "manual_online_lookup"

# ---------------------------------------------------------------------------
# v0.2.80 (Merge): Hersteller-zuerst für Dimensionen und Bilder
# ---------------------------------------------------------------------------
def test_manufacturer_domain_matching_prefers_longest_brand():
    from logic.pen_dimensions_service import manufacturer_domains_for_brand

    assert manufacturer_domains_for_brand("Pelikan") == ("pelikan.com",)
    assert manufacturer_domains_for_brand("LAMY") == ("lamy.com",)
    assert manufacturer_domains_for_brand("Faber-Castell") == ("faber-castell.com",)
    assert manufacturer_domains_for_brand("Graf von Faber-Castell")[0] == "graf-von-faber-castell.com"
    assert manufacturer_domains_for_brand("Pilot") == ("pilotpen.eu", "pilotpen.com")
    assert manufacturer_domains_for_brand("S.T. Dupont") == ("st-dupont.com",)
    # Token-Schutz: kein Substring-Fehltreffer
    assert manufacturer_domains_for_brand("Crossfield") == ()
    assert manufacturer_domains_for_brand("Unbekannte Marke") == ()
    assert manufacturer_domains_for_brand(None) == ()


def test_manufacturer_overlay_extends_and_overrides(tmp_path):
    import json as _json
    from logic import pen_dimensions_service as pds

    (tmp_path / "manufacturer_domains.json").write_text(
        _json.dumps({
            "Eigenmarke": "eigen.example",
            "Pelikan": ["pelikan.example", "pelikan-alt.example"],
        }),
        encoding="utf-8",
    )
    pds._manufacturer_overlay_cache = None  # Cache für Test zurücksetzen
    assert pds.manufacturer_domains_for_brand("Eigenmarke", data_dir=tmp_path) == ("eigen.example",)
    assert pds.manufacturer_domains_for_brand("Pelikan", data_dir=tmp_path) == (
        "pelikan.example", "pelikan-alt.example",
    )
    pds._manufacturer_overlay_cache = None


def test_dimension_search_is_ai_first_images_are_manufacturer_first():
    """v0.2.86: bewusst asymmetrische Reihenfolge (Nutzervorgabe).

    - Maße: KI-Stufe zuerst (fasst technische Daten zusammen), dann Hersteller.
    - Bilder: Hersteller zuerst (offizielle Produktfotos), dann KI.
    - Automatischer Parser-Pfad bleibt hersteller-zuerst (dort gibt es keine KI).
    """
    from logic.pen_dimensions_service import build_online_dimension_search_urls

    dim_urls = build_dimension_search_urls("Pilot", "Custom 74")
    img_urls = build_image_search_urls("Pilot", "Custom 74")
    online_urls = build_online_dimension_search_urls("Pilot", "Custom 74")

    # Maße: Stufe 1 = KI-Prompt, danach Hersteller-Domains.
    assert "udm=50" in dim_urls[0] and "site%3A" not in dim_urls[0]
    assert "site%3Apilotpen.eu" in dim_urls[1] and "Custom+74" in dim_urls[1]
    assert "site%3Apilotpen.com" in dim_urls[2]

    # Bilder: Stufe 1 = Hersteller-Bildersuche, KI danach.
    assert "site%3Apilotpen.eu" in img_urls[0] and "tbm=isch" in img_urls[0]
    ai_index = next(n for n, u in enumerate(img_urls) if "udm=50" in u)
    site_indices = [n for n, u in enumerate(img_urls) if "site%3A" in u]
    assert ai_index > max(site_indices)

    # site:-URLs bleiben in beiden Suchen minimal (kein Nulltreffer-Bug).
    for url in list(dim_urls) + list(img_urls):
        if "site%3A" in url:
            for forbidden in ("dimensions", "capacity", "filling", "%22"):
                assert forbidden not in url, (forbidden, url)

    # Offene Rückfallebene in beiden vorhanden.
    assert any(u.startswith("https://duckduckgo.com/?") for u in dim_urls)
    assert any(u.startswith("https://duckduckgo.com/?") for u in img_urls)

    # Automatischer Parser: hersteller-zuerst, minimal, gehaltvolle offene Phase.
    assert online_urls[0].startswith("https://html.duckduckgo.com/html/?")
    assert "site%3Apilotpen" in online_urls[0] and "dimensions" not in online_urls[0]
    assert "dimensions" in online_urls[-1]

    # Unbekannte Marke: keine site:-Stufe; Maße führen mit KI, Bilder ebenfalls.
    generic_dim = build_dimension_search_urls("Unbekannt", "X")
    generic_img = build_image_search_urls("Unbekannt", "X")
    assert "site%3A" not in generic_dim[0] and "udm=50" in generic_dim[0]
    assert "site%3A" not in generic_img[0] and "udm=50" in generic_img[0]

def test_is_manufacturer_source_matches_subdomains():
    from logic.pen_dimensions_service import _is_manufacturer_source

    assert _is_manufacturer_source("Pelikan", "https://shop.pelikan.com/m800")
    assert _is_manufacturer_source("Pelikan", "https://www.pelikan.com/m800")
    assert not _is_manufacturer_source("Pelikan", "https://pelikan.example-shop.com/x")
    assert not _is_manufacturer_source("Pelikan", None)


def test_online_lookup_prefers_manufacturer_page_over_web(tmp_path):
    search_manu = '<a href="https://www.pelikan.com/m800">M800</a><a href="https://retailer.example/m800">shop</a>'
    page_manu = "Pelikan M800 fountain pen. Length capped: 141 mm. Weight: 28 g. Piston filler."
    calls = []

    def fetcher(url, timeout_s):
        calls.append(url)
        if "duckduckgo" in url:
            return search_manu
        return page_manu

    result = lookup_pen_dimensions(
        "Pelikan", "M800",
        cache_path=tmp_path / "missing.json",
        allow_online=True,
        fetcher=fetcher,
    )
    assert result.best is not None
    assert result.best.source.startswith("manufacturer:")
    assert "pelikan.com" in result.best.source
    # Nur Herstellerlinks wurden geladen, der Händlerlink nicht:
    assert all("retailer.example" not in u for u in calls)


def test_online_lookup_falls_back_to_open_web_without_manufacturer_hit(tmp_path):
    page_web = "Lamy Safari fountain pen. Length capped: 139 mm. Weight: 17 g. Cartridge/converter."

    def fetcher(url, timeout_s):
        if "duckduckgo" in url and "site%3A" in url:
            return "<html>keine Treffer</html>"
        if "duckduckgo" in url:
            return '<a href="https://reviews.example/safari">Safari</a>'
        return page_web

    result = lookup_pen_dimensions(
        "Lamy", "Safari",
        cache_path=tmp_path / "missing.json",
        allow_online=True,
        fetcher=fetcher,
    )
    assert result.best is not None
    assert result.best.source.startswith("online:")


def test_online_lookup_early_stops_after_confident_manufacturer_hit(tmp_path):
    """Zweite Hersteller-Domain und offene Suche entfallen bei gutem Treffer."""
    page_manu = (
        "Pilot Custom 74 fountain pen. Length capped: 143 mm. Length posted: 156 mm. "
        "Diameter: 14.7 mm. Weight: 22 g. Ink capacity: 1.1 ml. Cartridge/converter."
    )
    calls = []

    def fetcher(url, timeout_s):
        calls.append(url)
        if "duckduckgo" in url:
            return '<a href="https://www.pilotpen.eu/custom74">Custom 74</a>'
        return page_manu

    from logic.pen_dimensions_service import lookup_online_dimensions
    out = lookup_online_dimensions("Pilot", "Custom 74", fetcher=fetcher)
    assert out and out[0].source.startswith("manufacturer:")
    searches = [u for u in calls if "duckduckgo" in u]
    assert len(searches) == 1  # early stop: pilotpen.com & offene Suche entfielen


# ---------------------------------------------------------------------------
# v0.2.85: Regression – überladene site:-Queries (Meldefall Essetio, Screenshot)
# ---------------------------------------------------------------------------
def test_site_queries_are_minimal_regression_essetio():
    """Der gemeldete Nulltreffer-Fall: site:faber-castell.com + 10 Pflichtwörter.

    Weder Voll-Phrase noch Exact-Phrase-Quoting dürfen je in eine site:-URL.
    """
    dim = build_dimension_search_urls("Faber-Castell", "Essetio")
    img = build_image_search_urls("Faber-Castell", "Essetio")
    from logic.pen_dimensions_service import build_online_dimension_search_urls
    auto = build_online_dimension_search_urls("Faber-Castell", "Essetio")

    assert "udm=50" in dim[0]  # Maße: KI zuerst (v0.2.86)
    assert dim[1] == "https://www.google.com/search?q=site%3Afaber-castell.com+Essetio"
    assert img[0] == "https://www.google.com/search?q=site%3Afaber-castell.com+Essetio&tbm=isch"
    assert auto[0] == "https://html.duckduckgo.com/html/?q=site%3Afaber-castell.com+Essetio"
    for url in list(dim) + list(img) + list(auto):
        if "site%3A" in url:
            for forbidden in ("dimensions", "capacity", "filling", "product", "%22"):
                assert forbidden not in url, (forbidden, url)


def test_site_query_falls_back_to_brand_without_model():
    dim = build_dimension_search_urls("Pelikan", "")
    img = build_image_search_urls("Pelikan", "")
    assert any("site%3Apelikan.com+Pelikan" in u for u in dim)
    assert "site%3Apelikan.com+Pelikan" in img[0]
