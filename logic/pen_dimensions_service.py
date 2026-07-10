"""Pen reference lookup helpers.

The service deliberately stays optional and safe:
- local/user cache first (offline, deterministic)
- optional online lookup second (generic search/page text parsing)
- browser search URLs as manual fallback
- no automatic database write; users explicitly approve suggestions

The historical name is kept because tests/imports already use
``pen_dimensions_service``.  Since v0.2.67 the same cache can also hold
filling data and image URLs.  Since v0.2.78 the online path can produce
structured suggestions instead of merely opening a browser search.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import html
import json
import re
import urllib.parse
import urllib.request
import unicodedata
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Iterable

DIMENSION_FIELDS = (
    "length_mm",
    "length_uncapped_mm",
    "length_posted_mm",
    "diameter_mm",
    "section_diameter_mm",
    "weight_g",
)

REFERENCE_NUMERIC_FIELDS = DIMENSION_FIELDS + ("ink_capacity_ml",)

SUPPORTED_FILL_SYSTEMS = {
    "piston",
    "vac",
    "converter",
    "cartridge",
    "eyedropper",
}

_FILL_SYSTEM_ALIASES = {
    "kolben": "piston",
    "piston filler": "piston",
    "piston-filler": "piston",
    "vacumatic": "vac",
    "vacuum": "vac",
    "vac filler": "vac",
    "vacuum filler": "vac",
    "konverter": "converter",
    "converter": "converter",
    "c/c": "converter",
    "cartridge converter": "converter",
    "cartridge/converter": "converter",
    "patrone": "cartridge",
    "cartridge": "cartridge",
    "eyedropper": "eyedropper",
    "eye dropper": "eyedropper",
}

MAX_ONLINE_BYTES = 900_000
DEFAULT_ONLINE_TIMEOUT_S = 8

# ---------------------------------------------------------------------------
# Hersteller-Verzeichnis (v0.2.79)
#
# Referenzdaten und Produktbilder sollen zuerst beim Hersteller gesucht werden,
# erst danach im offenen Netz.  Die Liste enthält nur etablierte, stabile
# Domains.  Fehlende oder geänderte Domains kann der Nutzer offline über eine
# Overlay-Datei ``manufacturer_domains.json`` im Datenverzeichnis ergänzen
# (Format: {"marke": "domain.tld"}), ohne dass Code angepasst werden muss.
# Ein falscher/fehlender Eintrag ist unkritisch: die generische Websuche läuft
# als zweite Stufe immer weiter.
# ---------------------------------------------------------------------------
MANUFACTURER_DOMAINS: dict[str, tuple[str, ...]] = {
    # Vereinigte Liste beider 0.2.79-Zweige.  Mehrere Domains je Marke sind
    # erlaubt (regionale Seiten, z. B. Pilot EU/US); die Suche probiert sie
    # der Reihe nach.  Einträge mit (unverifiziert) stammen aus dem Parallel-
    # zweig und sind offline nicht prüfbar – Fehleinträge kosten nichts, weil
    # die offene Websuche als letzte Stufe immer läuft und das Overlay
    # ``manufacturer_domains.json`` Korrekturen ohne Codeänderung erlaubt.
    "asvine": ("asvinepen.com",),                      # (unverifiziert)
    "aurora": ("aurorapen.it",),
    "benu": ("benupen.com",),
    "conklin": ("conklinpens.com",),
    "cross": ("cross.com",),
    "diplomat": ("diplomat-pen.com",),
    "edison": ("edisonpen.com",),
    "ensso": ("ensso.com",),
    "esterbrook": ("esterbrook.com", "esterbrookpens.com"),
    "faber castell": ("faber-castell.com",),
    "ferris wheel press": ("ferriswheelpress.com",),
    "franklin christoph": ("franklin-christoph.com",),
    "graf von faber castell": ("graf-von-faber-castell.com", "faber-castell.com"),
    "gravitas": ("gravitaspens.com",),                 # (unverifiziert)
    "hongdian": ("hongdianpen.com",),                  # (unverifiziert)
    "jinhao": ("jinhaopen.com",),                      # (unverifiziert)
    "karas": ("karaskustoms.com",),
    "kaweco": ("kaweco-pen.com",),
    "laban": ("laban.com",),                           # (unverifiziert)
    "lamy": ("lamy.com",),
    "leonardo": ("leonardoofficinaitaliana.com",),
    "majohn": ("majohn.com",),                         # (unverifiziert)
    "montblanc": ("montblanc.com",),
    "montegrappa": ("montegrappa.com",),
    "monteverde": ("monteverdepens.com",),
    "moonman": ("majohn.com",),                        # (unverifiziert)
    "nahvalur": ("nahvalur.com",),
    "nakaya": ("nakaya.org",),
    "namiki": ("pilot-namiki.com", "pilotpen.com"),
    "narwhal": ("nahvalur.com",),
    "opus 88": ("opus88.com.tw",),                     # (unverifiziert)
    "parker": ("parkerpen.com",),
    "pelikan": ("pelikan.com",),
    "pilot": ("pilotpen.eu", "pilotpen.com"),
    "pineider": ("pineider.com",),
    "platinum": ("platinum-pen.co.jp",),
    "retro 51": ("retro51.com",),
    "s t dupont": ("st-dupont.com",),
    "sailor": ("sailorpen.com", "sailor.co.jp"),
    "schon dsgn": ("schondsgn.com",),
    "sheaffer": ("sheaffer.com",),
    "stipula": ("stipula.it",),
    "twsbi": ("twsbi.com",),
    "visconti": ("visconti.it",),
    "waterman": ("waterman.com",),
}

_OVERLAY_STATE = SimpleNamespace(cache=None, path=None)


def load_manufacturer_overlay(data_dir: Path | None) -> dict[str, tuple[str, ...]]:
    """Nutzer-Overlay für Herstellerdomains laden (fehlertolerant, gecacht).

    Werte dürfen ein einzelner Domain-String oder eine Liste von Domains sein:
    ``{"asvine": "asvine.example"}`` oder ``{"pilot": ["pilotpen.eu", "pilotpen.com"]}``.
    """
    if data_dir is None:
        # Ohne expliziten Datenordner nur den eingebauten Katalog verwenden.
        # Ein zuvor geladener Test-/Fremdordner darf nicht global weiterwirken.
        return {}
    path = Path(data_dir) / "manufacturer_domains.json"
    if _OVERLAY_STATE.cache is not None and _OVERLAY_STATE.path == path:
        return _OVERLAY_STATE.cache
    overlay: dict[str, tuple[str, ...]] = {}
    try:
        if path.exists():
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                for key, value in raw.items():
                    if not isinstance(key, str):
                        continue
                    if isinstance(value, str):
                        domains = (value,)
                    elif isinstance(value, (list, tuple)):
                        domains = tuple(v for v in value if isinstance(v, str))
                    else:
                        continue
                    domains = tuple(d.strip().casefold() for d in domains if d.strip())
                    if domains:
                        overlay[normalize_pen_key(key, "")] = domains
    except Exception:
        overlay = {}
    _OVERLAY_STATE.cache = overlay
    _OVERLAY_STATE.path = path
    return overlay


def manufacturer_domains_for_brand(brand: str | None, *, data_dir: Path | None = None) -> tuple[str, ...]:
    """Bekannte Hersteller-Domains für eine Marke, sonst leeres Tuple.

    Matching ist token-basiert und bevorzugt den längsten Treffer, damit
    "Graf von Faber-Castell" nicht auf den "Faber-Castell"-Eintrag fällt.
    Token-Teilmengen statt Substrings verhindern Fehltreffer wie
    "Crossfield" → "cross".
    """
    norm = normalize_pen_key(brand or "", "")
    if not norm:
        return ()
    brand_tokens = set(norm.split())
    merged: dict[str, tuple[str, ...]] = dict(MANUFACTURER_DOMAINS)
    merged.update(load_manufacturer_overlay(data_dir))
    best_key = None
    for key in merged:
        key_tokens = key.split()
        if set(key_tokens) <= brand_tokens:
            if best_key is None or len(key_tokens) > len(best_key.split()):
                best_key = key
    return merged[best_key] if best_key else ()


def _is_manufacturer_source(brand: str, url: str | None, *, data_dir: Path | None = None) -> bool:
    """True, wenn die URL zu einer bekannten Hersteller-Domain der Marke gehört.

    endswith-Matching erkennt auch Subdomains (shop.pelikan.com).
    """
    if not url:
        return False
    host = urllib.parse.urlparse(url).netloc.casefold().replace("www.", "")
    return any(
        host == d or host.endswith("." + d)
        for domain in manufacturer_domains_for_brand(brand, data_dir=data_dir)
        for d in (domain.casefold().replace("www.", ""),)
    )

_FIELD_RULES: dict[str, dict[str, Any]] = {
    "length_mm": {
        "labels": (
            "length capped", "capped length", "closed length", "length closed",
            "length", "länge geschlossen", "geschlossen", "capped", "closed",
        ),
        "units": ("mm", "cm", "in", "inch", "inches"),
        "min": 80.0,
        "max": 250.0,
        "target": "mm",
    },
    "length_uncapped_mm": {
        "labels": ("uncapped length", "length uncapped", "open length", "länge offen", "uncapped", "open"),
        "units": ("mm", "cm", "in", "inch", "inches"),
        "min": 70.0,
        "max": 230.0,
        "target": "mm",
    },
    "length_posted_mm": {
        "labels": ("posted length", "length posted", "länge gepostet", "posted"),
        "units": ("mm", "cm", "in", "inch", "inches"),
        "min": 90.0,
        "max": 260.0,
        "target": "mm",
    },
    "diameter_mm": {
        "labels": ("max diameter", "barrel diameter", "diameter", "durchmesser max", "durchmesser"),
        "units": ("mm", "cm", "in", "inch", "inches"),
        "min": 6.0,
        "max": 30.0,
        "target": "mm",
    },
    "section_diameter_mm": {
        "labels": ("section diameter", "grip diameter", "grip", "section", "griffdurchmesser", "griff"),
        "units": ("mm", "cm", "in", "inch", "inches"),
        "min": 6.0,
        "max": 20.0,
        "target": "mm",
    },
    "weight_g": {
        "labels": ("weight", "gewicht"),
        "units": ("g", "gram", "grams"),
        "min": 3.0,
        "max": 120.0,
        "target": "g",
    },
    "ink_capacity_ml": {
        "labels": ("ink capacity", "capacity", "fill capacity", "füllvolumen", "tintenkapazität"),
        "units": ("ml", "cc"),
        "min": 0.2,
        "max": 6.0,
        "target": "ml",
    },
}


@dataclass(frozen=True)
class PenDimensionSuggestion:
    brand: str
    model: str
    source: str = "cache"
    length_mm: float | None = None
    length_uncapped_mm: float | None = None
    length_posted_mm: float | None = None
    diameter_mm: float | None = None
    section_diameter_mm: float | None = None
    weight_g: float | None = None
    fill_system: str | None = None
    ink_capacity_ml: float | None = None
    image_url: str | None = None
    image_urls: tuple[str, ...] = ()
    confidence: float = 0.0
    source_url: str | None = None
    notes: str = ""

    def values(self) -> dict[str, float]:
        """Only filled numeric dimensions, ready for Pen ORM assignment."""
        result: dict[str, float] = {}
        for field in DIMENSION_FIELDS:
            value = getattr(self, field)
            if value is not None and value > 0:
                result[field] = float(value)
        return result

    def capacity_values(self) -> dict[str, float]:
        value = self.ink_capacity_ml
        if value is not None and value > 0:
            return {"ink_capacity_ml": float(value)}
        return {}

    def reference_values(self) -> dict[str, Any]:
        """All safe structured values that may be applied to a Pen form."""
        result: dict[str, Any] = {**self.values(), **self.capacity_values()}
        fill_system = normalize_fill_system(self.fill_system)
        if fill_system:
            result["fill_system"] = fill_system
        urls = self.all_image_urls()
        if urls:
            result["image_url"] = urls[0]
        return result

    def all_image_urls(self) -> tuple[str, ...]:
        urls: list[str] = []
        for value in (self.image_url, *self.image_urls):
            if not value:
                continue
            text = str(value).strip()
            if text and text not in urls and _is_http_url(text):
                urls.append(text)
        return tuple(urls)

    def has_dimensions(self) -> bool:
        return bool(self.values())

    def has_reference_data(self) -> bool:
        return bool(self.reference_values())

    def to_json(self) -> dict[str, Any]:
        data = asdict(self)
        data["image_urls"] = list(self.all_image_urls())
        if not data.get("image_url") and data["image_urls"]:
            data["image_url"] = data["image_urls"][0]
        return data


@dataclass(frozen=True)
class PenDimensionLookupResult:
    query_brand: str
    query_model: str
    suggestions: tuple[PenDimensionSuggestion, ...]
    search_urls: tuple[str, ...]
    image_search_urls: tuple[str, ...] = ()
    message_code: str = "manual_online_lookup"

    @property
    def best(self) -> PenDimensionSuggestion | None:
        return self.suggestions[0] if self.suggestions else None


def normalize_pen_key(brand: str | None, model: str | None) -> str:
    raw = f"{brand or ''} {model or ''}".casefold().replace("ß", "ss")
    raw = unicodedata.normalize("NFKD", raw)
    raw = "".join(ch for ch in raw if not unicodedata.combining(ch))
    raw = re.sub(r"[^a-z0-9]+", " ", raw)
    return " ".join(raw.split())


def normalize_fill_system(value: str | None) -> str | None:
    if not value:
        return None
    raw = str(value).strip().casefold().replace("_", "-")
    raw = re.sub(r"\s+", " ", raw)
    if raw in SUPPORTED_FILL_SYSTEMS:
        return raw
    normalized = _FILL_SYSTEM_ALIASES.get(raw)
    if normalized in SUPPORTED_FILL_SYSTEMS:
        return normalized
    compact = raw.replace(" ", "-")
    if compact in SUPPORTED_FILL_SYSTEMS:
        return compact
    return None


def default_dimension_cache_path(data_dir: Path) -> Path:
    return Path(data_dir) / "pen_dimensions_cache.json"


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        text = str(value).strip().replace(",", ".")
        # Keep normal decimal values and ignore rough text snippets such as "ca. 1.2 ml".
        match = re.search(r"-?\d+(?:\.\d+)?", text)
        if not match:
            return None
        number = float(match.group(0))
        return number if number > 0 else None
    except (TypeError, ValueError):
        return None


def _is_http_url(value: str) -> bool:
    return value.startswith("https://") or value.startswith("http://")


def _coerce_image_urls(row: dict[str, Any]) -> tuple[str, ...]:
    raw_values: list[Any] = []
    for key in ("image_url", "image", "photo_url", "picture_url", "image_urls", "images", "photo_urls"):
        value = row.get(key)
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            raw_values.extend(value)
        else:
            raw_values.append(value)
    urls: list[str] = []
    for value in raw_values:
        text = str(value or "").strip()
        if text and _is_http_url(text) and text not in urls:
            urls.append(text)
    return tuple(urls)


def _suggestion_from_mapping(row: dict[str, Any], *, fallback_brand: str, fallback_model: str, source: str) -> PenDimensionSuggestion:
    image_urls = _coerce_image_urls(row)
    image_url = str(row.get("image_url") or row.get("photo_url") or "").strip() or None
    if image_url and not _is_http_url(image_url):
        image_url = None
    if not image_url and image_urls:
        image_url = image_urls[0]
    return PenDimensionSuggestion(
        brand=str(row.get("brand") or fallback_brand or "").strip(),
        model=str(row.get("model") or fallback_model or "").strip(),
        source=str(row.get("source") or source or "cache"),
        length_mm=_safe_float(row.get("length_mm") or row.get("length_capped_mm") or row.get("capped_length_mm")),
        length_uncapped_mm=_safe_float(row.get("length_uncapped_mm") or row.get("uncapped_length_mm")),
        length_posted_mm=_safe_float(row.get("length_posted_mm") or row.get("posted_length_mm")),
        diameter_mm=_safe_float(row.get("diameter_mm") or row.get("max_diameter_mm")),
        section_diameter_mm=_safe_float(row.get("section_diameter_mm") or row.get("grip_diameter_mm")),
        weight_g=_safe_float(row.get("weight_g") or row.get("weight")),
        fill_system=normalize_fill_system(row.get("fill_system") or row.get("filling_system") or row.get("filler")),
        ink_capacity_ml=_safe_float(row.get("ink_capacity_ml") or row.get("capacity_ml") or row.get("fill_volume_ml")),
        image_url=image_url,
        image_urls=image_urls,
        confidence=float(_safe_float(row.get("confidence")) or 0.0),
        source_url=str(row.get("source_url") or "").strip() or None,
        notes=str(row.get("notes") or "").strip(),
    )


def load_dimension_cache(cache_path: Path) -> list[PenDimensionSuggestion]:
    """Load a user-maintained pen reference cache.

    Supported JSON formats:
    - [{brand, model, length_mm, ink_capacity_ml, image_urls, ...}, ...]
    - {"pens": [...]} 
    - {"Pilot Custom 74": {brand, model, ...}}
    Invalid rows are ignored instead of breaking app startup.
    """
    path = Path(cache_path)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    if isinstance(data, dict) and isinstance(data.get("pens"), list):
        rows: Iterable[Any] = data["pens"]
    elif isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        expanded = []
        for key, value in data.items():
            if isinstance(value, dict):
                row = {"model": key, **value}
                expanded.append(row)
        rows = expanded
    else:
        rows = []

    suggestions: list[PenDimensionSuggestion] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        suggestion = _suggestion_from_mapping(row, fallback_brand="", fallback_model="", source="cache")
        if (suggestion.brand or suggestion.model) and suggestion.has_reference_data():
            suggestions.append(suggestion)
    return suggestions


def save_dimension_cache(cache_path: Path, suggestions: Iterable[PenDimensionSuggestion]) -> None:
    path = Path(cache_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"pens": [s.to_json() for s in suggestions if s.has_reference_data()]}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def merge_dimension_cache(cache_path: Path, suggestion: PenDimensionSuggestion) -> None:
    """Store an approved reference suggestion without creating duplicates.

    The cache remains user-maintained: online suggestions are persisted only after
    the UI has asked the user to apply them. Existing manual rows win unless the
    new row provides additional fields.
    """
    if not suggestion.has_reference_data():
        return
    rows = load_dimension_cache(cache_path)
    new_key = normalize_pen_key(suggestion.brand, suggestion.model)
    merged: list[PenDimensionSuggestion] = []
    replaced = False
    for row in rows:
        if normalize_pen_key(row.brand, row.model) != new_key:
            merged.append(row)
            continue
        data = row.to_json()
        for key, value in suggestion.to_json().items():
            if key in {"brand", "model"}:
                continue
            if key == "image_urls":
                existing = data.get("image_urls") or []
                for url in value or []:
                    if url and url not in existing:
                        existing.append(url)
                data["image_urls"] = existing
                if not data.get("image_url") and existing:
                    data["image_url"] = existing[0]
                continue
            if value not in (None, "", [], ()) and data.get(key) in (None, "", [], (), 0, 0.0):
                data[key] = value
        merged.append(_suggestion_from_mapping(data, fallback_brand=row.brand, fallback_model=row.model, source=row.source or "cache"))
        replaced = True
    if not replaced:
        merged.append(suggestion)
    save_dimension_cache(cache_path, merged)


def match_cached_dimensions(
    brand: str,
    model: str,
    cache: Iterable[PenDimensionSuggestion],
    *,
    min_confidence: float = 0.55,
) -> list[PenDimensionSuggestion]:
    query_key = normalize_pen_key(brand, model)
    if not query_key:
        return []
    scored: list[tuple[float, PenDimensionSuggestion]] = []
    query_parts = set(query_key.split())
    for item in cache:
        item_key = normalize_pen_key(item.brand, item.model)
        if not item_key or not item.has_reference_data():
            continue
        item_parts = set(item_key.split())
        overlap = len(query_parts & item_parts) / max(1, len(query_parts | item_parts))
        exact_bonus = 0.35 if item_key == query_key else 0.0
        containment_bonus = 0.20 if query_key in item_key or item_key in query_key else 0.0
        stated_conf = max(0.0, min(1.0, float(item.confidence or 0.0)))
        confidence = min(1.0, overlap + exact_bonus + containment_bonus + stated_conf * 0.15)
        if confidence >= min_confidence:
            scored.append((confidence, PenDimensionSuggestion(
                brand=item.brand,
                model=item.model,
                source=item.source,
                length_mm=item.length_mm,
                length_uncapped_mm=item.length_uncapped_mm,
                length_posted_mm=item.length_posted_mm,
                diameter_mm=item.diameter_mm,
                section_diameter_mm=item.section_diameter_mm,
                weight_g=item.weight_g,
                fill_system=normalize_fill_system(item.fill_system),
                ink_capacity_ml=item.ink_capacity_ml,
                image_url=item.image_url,
                image_urls=item.all_image_urls(),
                confidence=confidence,
                source_url=item.source_url,
                notes=item.notes,
            )))
    scored.sort(key=lambda pair: (pair[0], pair[1].brand, pair[1].model), reverse=True)
    return [s for _score, s in scored]


def _duckduckgo_search_url(query: str, *, images: bool = False, html_endpoint: bool = False) -> str:
    encoded = urllib.parse.urlencode({"q": query.strip()})
    if html_endpoint:
        # klassischer, stabilerer HTML-Endpunkt (weniger JS-/Anomalie-Umleitungen)
        return f"https://html.duckduckgo.com/html/?{encoded}"
    if images:
        return f"https://duckduckgo.com/?iar=images&iax=images&ia=images&{encoded}"
    return f"https://duckduckgo.com/?{encoded}"


def _google_search_url(query: str, *, images: bool = False, ai_mode: bool = False) -> str:
    """Build a user-facing Google URL.

    ``ai_mode`` intentionally only adds Google's lightweight AI-mode hint.
    If that mode is not available for the user's account/region, Google still
    opens a normal search for the same prompt.  Manual lookup must remain useful
    without relying on a specific Google UI rollout.
    """
    params = {"q": query.strip()}
    if images:
        params["tbm"] = "isch"
    if ai_mode and not images:
        params["udm"] = "50"
    return f"https://www.google.com/search?{urllib.parse.urlencode(params)}"


def _quoted_pen_name(brand: str, model: str) -> str:
    name = " ".join(part.strip() for part in (brand or "", model or "") if part and part.strip())
    return f'"{name}"' if name else ""


def _site_query_terms(brand: str, model: str) -> str:
    """Suchbegriffe für ``site:``-Phasen – bewusst minimal (v0.2.85).

    Auf der Hersteller-Domain ist die Marke durch die Domain gegeben. Jedes
    zusätzliche Pflichtwort ("dimensions", "ink capacity" …) und erst recht ein
    Exact-Phrase-Quoting siebt real existierende Produktseiten aus, weil
    Suchmaschinen alle Begriffe gleichzeitig verlangen -> garantiert 0 Treffer.
    Gemeldeter Praxisfall: Faber-Castell Essetio. Nur der Modellname trifft;
    die Voll-Phrasen bleiben der offenen Web-/KI-Phase vorbehalten.
    Fallback ohne Modell: Marke.
    """
    return (model or "").strip() or (brand or "").strip()


def _dimension_query(brand: str, model: str) -> str:
    # Parser-/Fallback-Query: kompakt, technisch, ohne natürliche Sprache.
    return " ".join(
        part
        for part in (
            _quoted_pen_name(brand, model),
            "fountain pen",
            "dimensions",
            "length",
            "weight",
            "ink capacity",
            "filling system",
        )
        if part
    ).strip()


def _dimension_ai_query(brand: str, model: str) -> str:
    name = _quoted_pen_name(brand, model) or "this fountain pen"
    return (
        f"{name} fountain pen dimensions: closed length, uncapped length, "
        "posted length, weight, ink capacity and filling system. Prefer official "
        "manufacturer, shop or review sources and show the source names."
    )


def _image_query(brand: str, model: str) -> str:
    return " ".join(
        part
        for part in (_quoted_pen_name(brand, model), "fountain pen", "product images", "official photos")
        if part
    ).strip()


def _image_ai_query(brand: str, model: str) -> str:
    name = _quoted_pen_name(brand, model) or "this fountain pen"
    return (
        f"Find official product photos or reliable shop images for {name} fountain pen. "
        "Prefer manufacturer pages, then reputable shops. Show image/source links."
    )


def build_dimension_search_urls(brand: str, model: str, *, data_dir: Path | None = None) -> tuple[str, ...]:
    """Manuelle Recherche-URLs für Maße – **KI zuerst** (v0.2.86).

    Reihenfolge auf Nutzerwunsch:
      1. Google KI-/Websuche mit natürlichsprachigem Prompt (``udm=50``).
         Die KI-Übersicht fasst Maße aus mehreren Quellen zusammen und nennt
         sie – für technische Daten ist das der schnellste Weg. Ist der
         KI-Modus nicht verfügbar, öffnet Google normal denselben Prompt.
      2. Hersteller-Domain(s), ``site:<domain> <Modell>`` – minimal
         formuliert (überladene site:-Queries liefern strukturell 0 Treffer).
         Bleibt als belastbare Primärquelle erhalten.
      3. Klassische Google-/DuckDuckGo-Suche als Rückfallebene.

    Für **Bilder** gilt bewusst die umgekehrte Priorität (Hersteller zuerst),
    siehe :func:`build_image_search_urls`.
    """
    query = _dimension_query(brand, model)
    ai_query = _dimension_ai_query(brand, model)
    site_terms = _site_query_terms(brand, model)
    urls: list[str] = [_google_search_url(ai_query, ai_mode=True)]
    for domain in manufacturer_domains_for_brand(brand, data_dir=data_dir):
        urls.append(_google_search_url(f"site:{domain} {site_terms}".strip()))
    urls.append(_google_search_url(query))
    urls.append(_duckduckgo_search_url(query))
    return tuple(dict.fromkeys(urls))


def build_image_search_urls(brand: str, model: str, *, data_dir: Path | None = None) -> tuple[str, ...]:
    """Manuelle Recherche-URLs für Bilder – **Hersteller zuerst** (v0.2.86).

    Bewusst umgekehrt zur Maße-Suche: Bei Produktfotos ist die offizielle
    Herstellerquelle das Ziel (korrekte Farbe, Finish, aktuelle Ausführung),
    nicht eine zusammengefasste Übersicht. Reihenfolge:
      1. Hersteller-Domain(s) als Bildersuche, minimal formuliert.
      2. Google KI-/Websuche (findet offizielle Fotos und nennt Quellen).
      3. Offene Bildersuche (Google Images, DuckDuckGo) als Rückfallebene.
    """
    query = _image_query(brand, model)
    ai_query = _image_ai_query(brand, model)
    site_terms = _site_query_terms(brand, model)
    urls: list[str] = []
    for domain in manufacturer_domains_for_brand(brand, data_dir=data_dir):
        urls.append(_google_search_url(f"site:{domain} {site_terms}".strip(), images=True))
    urls.append(_google_search_url(ai_query, ai_mode=True))
    urls.append(_google_search_url(query, images=True))
    urls.append(_duckduckgo_search_url(query, images=True))
    return tuple(dict.fromkeys(urls))


def build_online_dimension_search_urls(brand: str, model: str, *, data_dir: Path | None = None) -> tuple[str, ...]:
    """Such-URLs für den automatischen Online-Lookup, Hersteller zuerst.

    Der HTML-Endpunkt ist für Parser und Tests stabiler als das JS-Frontend.
    """
    query = _dimension_query(brand, model)
    site_terms = _site_query_terms(brand, model)
    urls: list[str] = []
    for domain in manufacturer_domains_for_brand(brand, data_dir=data_dir):
        urls.append(_duckduckgo_search_url(f"site:{domain} {site_terms}".strip(), html_endpoint=True))
    urls.append(_duckduckgo_search_url(query, html_endpoint=True))
    return tuple(dict.fromkeys(urls))


Fetcher = Callable[[str, int], str]


def _strip_html(raw: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", raw or "")
    text = re.sub(r"(?is)<br\s*/?>", "\n", text)
    text = re.sub(r"(?is)</(p|div|li|tr|td|th|h\d)>", "\n", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"[\u00a0\t\r]+", " ", text)
    text = re.sub(r"\n\s+", "\n", text)
    return re.sub(r"[ ]{2,}", " ", text).strip()


def _plain_for_regex(text: str) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"[\u2013\u2014]", "-", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _convert_number(value: float, unit: str, target: str) -> float | None:
    unit = (unit or "").casefold().strip().replace(".", "")
    number = float(value)
    if target == "mm":
        if unit == "cm":
            number *= 10.0
        elif unit in {"in", "inch", "inches"}:
            number *= 25.4
        elif unit != "mm":
            return None
    elif target == "g":
        if unit not in {"g", "gram", "grams"}:
            return None
    elif target == "ml":
        if unit not in {"ml", "cc"}:
            return None
    return round(number, 2)


def _in_range(value: float | None, rule: dict[str, Any]) -> bool:
    if value is None:
        return False
    return float(rule["min"]) <= value <= float(rule["max"])


def _extract_field_value(text: str, field: str) -> float | None:
    rule = _FIELD_RULES[field]
    unit_group = "|".join(re.escape(unit) for unit in rule["units"])
    best: tuple[int, float] | None = None
    for label in rule["labels"]:
        label_rx = re.escape(label).replace(r"\ ", r"[\s_/-]+")
        # Prefer values that occur shortly after a clear label. This handles tables
        # and snippets such as "Length capped: 140 mm" or "Weight - 24 g".
        pattern = re.compile(
            rf"(?i)(?<![a-z0-9]){label_rx}(?![a-z0-9])"
            rf"[^\d]{{0,80}}(\d{{1,3}}(?:[\.,]\d{{1,2}})?)\s*({unit_group})\b"
        )
        for match in pattern.finditer(text):
            context = text[max(0, match.start(0) - 18): match.start(1)].casefold()
            if field == "length_mm" and re.search(r"\b(uncapped|posted|open|offen|gepostet)\b", context):
                continue
            if field == "diameter_mm" and re.search(r"\b(section|grip|griff|gripsection)\b", context):
                continue
            raw = match.group(1).replace(",", ".")
            value = _convert_number(float(raw), match.group(2), str(rule["target"]))
            if _in_range(value, rule):
                # Shorter label-to-value distance is usually the right table cell.
                distance = match.start(1) - match.start(0)
                candidate = (distance, float(value))
                if best is None or candidate[0] < best[0]:
                    best = candidate
    return best[1] if best else None


def _extract_fill_system(text: str) -> str | None:
    haystack = f" {text.casefold()} "
    ordered = [
        ("vacuum filler", "vac"),
        ("vac filler", "vac"),
        ("vacumatic", "vac"),
        ("piston filler", "piston"),
        ("piston-filler", "piston"),
        ("kolben", "piston"),
        ("cartridge/converter", "converter"),
        ("cartridge converter", "converter"),
        ("converter", "converter"),
        ("konverter", "converter"),
        ("cartridge", "cartridge"),
        ("patrone", "cartridge"),
        ("eyedropper", "eyedropper"),
    ]
    for needle, normalized in ordered:
        if needle in haystack:
            return normalized
    return None


def extract_dimension_suggestion_from_text(
    brand: str,
    model: str,
    text: str,
    *,
    source_url: str | None = None,
    source: str = "online",
) -> PenDimensionSuggestion | None:
    """Extract one structured reference suggestion from search/page text.

    The parser is intentionally conservative: it only accepts values with an
    explicit nearby label and unit, then validates them against plausible pen
    ranges. Ambiguous bare numbers are ignored.
    """
    plain = _plain_for_regex(_strip_html(text) if "<" in (text or "") and ">" in (text or "") else text)
    if not plain:
        return None
    values = {field: _extract_field_value(plain, field) for field in REFERENCE_NUMERIC_FIELDS}
    values = {field: value for field, value in values.items() if value is not None}
    fill_system = _extract_fill_system(plain)
    if not values and not fill_system:
        return None

    norm_text = normalize_pen_key(plain, "")
    brand_tokens = set(normalize_pen_key(brand, "").split())
    model_tokens = set(normalize_pen_key("", model).split())
    brand_hits = len(brand_tokens & set(norm_text.split())) if brand_tokens else 0
    model_hits = len(model_tokens & set(norm_text.split())) if model_tokens else 0
    identity_score = 0.0
    if brand_tokens:
        identity_score += min(0.3, brand_hits / max(1, len(brand_tokens)) * 0.3)
    if model_tokens:
        identity_score += min(0.35, model_hits / max(1, len(model_tokens)) * 0.35)
    field_score = min(0.35, len(values) * 0.07 + (0.05 if fill_system else 0.0))
    confidence = round(min(0.98, identity_score + field_score), 2)

    # Avoid proposing unrelated search result noise. If the source text does not
    # mention either brand or model, require at least three structured values.
    if identity_score < 0.25 and len(values) < 3:
        return None

    return PenDimensionSuggestion(
        brand=brand.strip(),
        model=model.strip(),
        source=source,
        length_mm=values.get("length_mm"),
        length_uncapped_mm=values.get("length_uncapped_mm"),
        length_posted_mm=values.get("length_posted_mm"),
        diameter_mm=values.get("diameter_mm"),
        section_diameter_mm=values.get("section_diameter_mm"),
        weight_g=values.get("weight_g"),
        fill_system=fill_system,
        ink_capacity_ml=values.get("ink_capacity_ml"),
        confidence=confidence,
        source_url=source_url,
    )


def _fetch_url_text(url: str, timeout_s: int = DEFAULT_ONLINE_TIMEOUT_S) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "FountainPenManager/0.2.86 reference lookup (+user approved)",
            "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.3",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as response:  # nosec: user-triggered reference lookup
        raw = response.read(MAX_ONLINE_BYTES + 1)
    if len(raw) > MAX_ONLINE_BYTES:
        raw = raw[:MAX_ONLINE_BYTES]
    content_type = ""
    try:
        content_type = response.headers.get_content_charset() or "utf-8"
    except Exception:
        content_type = "utf-8"
    return raw.decode(content_type or "utf-8", errors="replace")


def _extract_candidate_links(search_html: str) -> list[str]:
    links: list[str] = []
    for raw in re.findall(r'href=["\']([^"\']+)["\']', search_html or "", flags=re.I):
        href = html.unescape(raw)
        if href.startswith("//"):
            href = "https:" + href
        if "duckduckgo.com/l/?" in href:
            parsed = urllib.parse.urlparse(href)
            query = urllib.parse.parse_qs(parsed.query)
            href = query.get("uddg", [href])[0]
        if not href.startswith(("https://", "http://")):
            continue
        host = urllib.parse.urlparse(href).netloc.casefold()
        if not host or "duckduckgo.com" in host or "google." in host:
            continue
        if href not in links:
            links.append(href)
        if len(links) >= 5:
            break
    return links


def _domain_label(url: str | None) -> str:
    if not url:
        return "online"
    try:
        host = urllib.parse.urlparse(url).netloc or "online"
        return f"online:{host.replace('www.', '')}"
    except Exception:
        return "online"


def _phase_plan(brand: str, model: str, *, data_dir: Path | None) -> list[tuple[str | None, str]]:
    """Suchphasen als (domain|None, such_url): Hersteller-Domains zuerst, dann offen."""
    query = _dimension_query(brand, model)
    plan: list[tuple[str | None, str]] = []
    for domain in manufacturer_domains_for_brand(brand, data_dir=data_dir):
        plan.append((domain, _duckduckgo_search_url(f"site:{domain} {_site_query_terms(brand, model)}".strip(), html_endpoint=True)))
    plan.append((None, _duckduckgo_search_url(query, html_endpoint=True)))
    seen: set[str] = set()
    unique: list[tuple[str | None, str]] = []
    for domain, url in plan:
        if url in seen:
            continue
        seen.add(url)
        unique.append((domain, url))
    return unique


def lookup_online_dimensions(
    brand: str,
    model: str,
    *,
    timeout_s: int = DEFAULT_ONLINE_TIMEOUT_S,
    fetcher: Fetcher | None = None,
    min_confidence: float = 0.55,
    data_dir: Path | None = None,
) -> list[PenDimensionSuggestion]:
    """Return conservative online suggestions, or an empty list on errors/offline.

    Merge beider 0.2.79-Zweige:
    - Phasen laufen Hersteller-Domain(s) zuerst, danach offenes Netz; ein
      Herstellertreffer mit Konfidenz >= 0.65 stoppt vor Shop-/Forenrauschen.
    - In Herstellerphasen werden Ergebnislinks strikt auf die jeweilige Domain
      gefiltert (inkl. Subdomains), damit keine Fremdseiten geladen werden.
    - Herstellertreffer werden als ``manufacturer:<host>`` markiert und in der
      Sortierung vor allen Webtreffern gereiht.
    - Wertidentische Treffer aus Spiegel-Snippets werden dedupliziert.

    ``fetcher`` is injectable for tests and keeps unit tests network-free. Runtime
    uses urllib only when the UI explicitly requests an online lookup.
    """
    fetch = fetcher or _fetch_url_text
    suggestions: list[PenDimensionSuggestion] = []

    def _host_matches(url: str, domain: str) -> bool:
        host = urllib.parse.urlparse(url).netloc.casefold().replace("www.", "")
        d = domain.casefold().replace("www.", "")
        return host == d or host.endswith("." + d)

    for domain, search_url in _phase_plan(brand, model, data_dir=data_dir):
        try:
            search_html = fetch(search_url, timeout_s)
        except Exception:
            continue

        # Search snippets sometimes already contain the data. Add them as a
        # low-cost candidate before fetching top result pages.
        search_text = _strip_html(search_html)
        first = extract_dimension_suggestion_from_text(
            brand,
            model,
            search_text,
            source_url=search_url,
            source=("manufacturer:search" if domain else "online:search"),
        )
        if first and first.confidence >= min_confidence:
            fingerprint = (first.values(), first.ink_capacity_ml, first.fill_system)
            if not any((x.values(), x.ink_capacity_ml, x.fill_system) == fingerprint for x in suggestions):
                suggestions.append(first)

        links = _extract_candidate_links(search_html)
        if domain:
            links = [u for u in links if _host_matches(u, domain)]
        for url in links[:4]:
            try:
                page = fetch(url, timeout_s)
            except Exception:
                continue
            is_maker = bool(domain) or _is_manufacturer_source(brand, url, data_dir=data_dir)
            host = urllib.parse.urlparse(url).netloc.replace("www.", "")
            suggestion = extract_dimension_suggestion_from_text(
                brand,
                model,
                page,
                source_url=url,
                source=(f"manufacturer:{host}" if is_maker else _domain_label(url)),
            )
            if not suggestion or suggestion.confidence < min_confidence:
                continue
            # Avoid duplicate field-identical suggestions from mirrored snippets.
            fingerprint = (suggestion.values(), suggestion.ink_capacity_ml, suggestion.fill_system)
            if any((x.values(), x.ink_capacity_ml, x.fill_system) == fingerprint for x in suggestions):
                continue
            suggestions.append(suggestion)

        # Herstellertreffer gut genug: vor Shop-/Forenrauschen stoppen.
        if any(x.source.startswith("manufacturer:") and x.confidence >= 0.65 for x in suggestions):
            break

    suggestions.sort(
        key=lambda item: (
            1 if item.source.startswith("manufacturer:") or _is_manufacturer_source(brand, item.source_url, data_dir=data_dir) else 0,
            item.confidence,
            len(item.reference_values()),
        ),
        reverse=True,
    )
    return suggestions[:3]


def lookup_pen_dimensions(
    brand: str,
    model: str,
    *,
    cache_path: Path | None = None,
    allow_online: bool = False,
    timeout_s: int = DEFAULT_ONLINE_TIMEOUT_S,
    fetcher: Fetcher | None = None,
) -> PenDimensionLookupResult:
    cache = load_dimension_cache(cache_path) if cache_path else []
    matches = match_cached_dimensions(brand, model, cache)
    data_dir = cache_path.parent if cache_path else None
    urls = build_dimension_search_urls(brand, model, data_dir=data_dir)
    image_urls = build_image_search_urls(brand, model, data_dir=data_dir)
    message_code = "cache_match" if matches else "manual_online_lookup"
    if not matches and allow_online:
        matches = lookup_online_dimensions(brand, model, timeout_s=timeout_s, fetcher=fetcher, data_dir=data_dir)
        message_code = "online_match" if matches else "manual_online_lookup"
    return PenDimensionLookupResult(
        query_brand=brand,
        query_model=model,
        suggestions=tuple(matches),
        search_urls=urls,
        image_search_urls=image_urls,
        message_code=message_code,
    )
