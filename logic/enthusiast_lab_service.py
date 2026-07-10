"""Optionale Enthusiasten-Funktionen für Füller- und Tinten-Sammler.

Das Modul ist bewusst Qt-frei. Die App kann damit tiefe Sammler-Workflows
anbieten, ohne die normale Inventar-Nutzung zu erzwingen:
- Tinten-Restmengen / Nachkauf
- Feder-Tausch-Historie
- Farbfamilien-Lückenanalyse
- Reinigungsprotokoll-Auswertung
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from statistics import mean
from typing import Any, Iterable

from logic.color_family_service import normalize_color_family


@dataclass(frozen=True)
class InkStockRow:
    ink_id: int | None
    label: str
    remaining_ml: float | None
    bottle_size_ml: float | None
    fill_pct: float | None
    status: str
    recommendation: str
    threshold_ml: float


@dataclass(frozen=True)
class ColorGapRow:
    family: str
    owned_count: int
    status: str
    recommendation: str
    examples: tuple[str, ...] = ()


@dataclass(frozen=True)
class NibHistoryRow:
    pen_id: int | None
    pen_label: str
    nib_id: int | None
    nib_label: str
    installed_date: datetime | None
    removed_date: datetime | None
    active: bool
    days_installed: int | None
    notes: str


@dataclass(frozen=True)
class CleaningStatsRow:
    ink_id: int | None
    ink_label: str
    cleanings: int
    avg_minutes: float | None
    avg_difficulty: float | None
    avg_flush_cycles: float | None
    last_cleaned_at: datetime | None
    status: str


WARM_BROWN_HINTS = ("sepia", "warm brown", "warmbraun", "cognac", "caramel", "amber", "honig", "mahogany")
COOL_GREY_HINTS = ("grey", "gray", "grau", "smoke", "graphite", "slate")
BUSINESS_BLUE_HINTS = ("blue", "blau", "navy", "royal")

RECOMMENDED_FAMILIES: dict[str, str] = {
    "blue": "business_blue",
    "black": "document_black",
    "green": "deep_green",
    "red": "red_burgundy",
    "brown": "warm_brown",
    "grey": "cool_grey",
    "teal": "teal_petrol",
    "purple": "purple_violet",
}


def _label(obj: Any, *fields: str, fallback: str = "—") -> str:
    if obj is None:
        return fallback
    values = [str(getattr(obj, field, "") or "").strip() for field in fields]
    return " ".join(v for v in values if v).strip() or fallback


def _ink_label(ink: Any) -> str:
    return _label(ink, "brand", "name", fallback="—")


def _pen_label(pen: Any) -> str:
    return _label(pen, "brand", "model", fallback="—")


def _nib_label(nib: Any) -> str:
    display = getattr(nib, "display_label", None)
    if display:
        return str(display)
    return _label(nib, "manufacturer", "physical_size", "size", "grind", fallback="—")


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def _safe_int(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except Exception:
        return None


def apply_ink_consumption(remaining_ml: float | None, volume_ml: float | None) -> float | None:
    """Zieht eine reale Befüllmenge vom Tintenrest ab, nie unter 0.

    Wichtig: Diese Funktion ist reine Logik. Sie soll beim Befüllen verwendet
    werden, nicht beim Reinigen. So wird die v0.2.59-Denkfalle vermieden, bei
    der Tinte erst beim Reinigen oder sogar doppelt abgezogen werden konnte.
    """
    remaining = _safe_float(remaining_ml)
    volume = _safe_float(volume_ml)
    if remaining is None:
        return None
    if volume is None or volume <= 0:
        return remaining
    return max(0.0, remaining - volume)


def ink_fill_status(ink: Any, *, default_threshold_ml: float = 5.0) -> dict[str, Any]:
    """Kompatible Einzelauswertung für Detailansichten und alte Tests.

    ``ink_stock_rows`` ist die tabellarische Hauptlogik. Diese Funktion liefert
    zusätzlich ein kleines Dict wie die v0.2.59-Linie, nutzt aber die neue
    Nachkauf-Schwelle und trennt leer/nachkaufen/niedrig/ok sauber.
    """
    row = ink_stock_rows([ink], default_threshold_ml=default_threshold_ml)[0]
    return {
        "remaining_ml": row.remaining_ml,
        "bottle_size_ml": row.bottle_size_ml,
        "pct": row.fill_pct,
        "level": row.status,
        "recommendation": row.recommendation,
        "threshold_ml": row.threshold_ml,
    }


def restock_recommendations(inks: Iterable[Any]) -> list[dict[str, Any]]:
    """Gibt nur Tinten zurück, bei denen eine Aktion sinnvoll ist.

    Unbekannte Füllstände werden nicht als Nachkauf empfohlen; sie gehören ins
    Enthusiasten-Lab unter ``measure_bottle``.
    """
    actionable = []
    for row in ink_stock_rows([ink for ink in inks if not bool(getattr(ink, "is_archived", False))]):
        if row.status in {"empty", "reorder", "low"}:
            actionable.append({
                "id": row.ink_id,
                "label": row.label,
                "level": row.status,
                "pct": row.fill_pct,
                "remaining_ml": row.remaining_ml,
                "recommendation": row.recommendation,
            })
    return actionable


def build_sample_grid(samples: Iterable[Any], columns: int = 3) -> list[list[Any]]:
    """Ordnet Schreibproben zeilenweise in ein UI-Grid ein.

    Das übernimmt die gute v0.2.59-Idee, bleibt aber rein optional und ohne
    Datenbankbindung.
    """
    cols = max(1, int(columns or 1))
    items = list(samples)
    return [items[i:i + cols] for i in range(0, len(items), cols)]


def compare_axis_options(samples: Iterable[Any]) -> dict[str, bool]:
    """Ermittelt, welche Vergleichsachsen für eine Probenauswahl Sinn ergeben."""
    values = {"ink": set(), "paper": set(), "pen": set()}
    for sample in samples:
        values["ink"].add(getattr(sample, "ink_id", None))
        values["paper"].add(getattr(sample, "paper_id", None))
        values["pen"].add(getattr(sample, "pen_id", None))
    return {key: len({v for v in vals if v is not None}) >= 2 for key, vals in values.items()}


def ink_stock_rows(
    inks: Iterable[Any],
    *,
    default_threshold_ml: float = 5.0,
    low_percent_threshold: float = 15.0,
) -> list[InkStockRow]:
    """Bewertet Restmengen und erzeugt Nachkauf-Empfehlungen.

    Pro Tinte kann optional ``reorder_threshold_ml`` gesetzt sein. Ohne diese
    Angabe nutzt die Auswertung einen konservativen Default. Unvollständige
    Daten bleiben sichtbar, lösen aber keine harten Fehler aus.
    """
    rows: list[InkStockRow] = []
    for ink in inks:
        remaining = _safe_float(getattr(ink, "remaining_ml", None))
        size = _safe_float(getattr(ink, "bottle_size_ml", None))
        threshold = _safe_float(getattr(ink, "reorder_threshold_ml", None)) or float(default_threshold_ml)
        fill_pct = None
        if remaining is not None and size and size > 0:
            fill_pct = max(0.0, min(100.0, remaining / size * 100.0))

        is_empty = bool(getattr(ink, "is_empty", False)) or (remaining is not None and remaining <= 0)
        if is_empty:
            status, recommendation = "empty", "replace_or_archive"
        elif remaining is None:
            status, recommendation = "unknown", "measure_bottle"
        elif remaining <= threshold:
            status, recommendation = "reorder", "buy_again_if_loved"
        elif fill_pct is not None and fill_pct <= low_percent_threshold:
            status, recommendation = "low", "watch_next_orders"
        else:
            status, recommendation = "ok", "no_action"

        rows.append(InkStockRow(
            ink_id=getattr(ink, "id", None),
            label=_ink_label(ink),
            remaining_ml=remaining,
            bottle_size_ml=size,
            fill_pct=fill_pct,
            status=status,
            recommendation=recommendation,
            threshold_ml=threshold,
        ))
    severity = {"empty": 0, "reorder": 1, "low": 2, "unknown": 3, "ok": 4}
    return sorted(rows, key=lambda r: (severity.get(r.status, 9), r.label.lower()))


def color_gap_rows(inks: Iterable[Any]) -> list[ColorGapRow]:
    """Analysiert, welche Farbfamilien in der Sammlung fehlen.

    Zusätzlich zur groben Familie erkennt die Logik die besonders nützliche
    Lücke "warmes Braun" über color_type/notes/name. Dadurch ist die Ausgabe
    praxisnäher als reine Farbenzählung.
    """
    counts: dict[str, int] = {}
    examples: dict[str, list[str]] = {}
    warm_brown = False
    cool_grey = False
    business_blue = False

    for ink in inks:
        if bool(getattr(ink, "is_archived", False)) or bool(getattr(ink, "is_empty", False)):
            continue
        remaining = _safe_float(getattr(ink, "remaining_ml", None))
        if remaining is not None and remaining <= 0:
            continue
        family = normalize_color_family(getattr(ink, "color_family", None)) or "other"
        counts[family] = counts.get(family, 0) + 1
        examples.setdefault(family, []).append(_ink_label(ink))
        hay = " ".join(str(getattr(ink, field, "") or "").lower() for field in ("name", "color_type", "notes", "character_notes"))
        if family == "brown" and any(h in hay for h in WARM_BROWN_HINTS):
            warm_brown = True
        if family == "grey" and any(h in hay for h in COOL_GREY_HINTS):
            cool_grey = True
        if family == "blue" and any(h in hay for h in BUSINESS_BLUE_HINTS):
            business_blue = True

    rows: list[ColorGapRow] = []
    for family, recommendation in RECOMMENDED_FAMILIES.items():
        count = counts.get(family, 0)
        status = "missing" if count == 0 else ("thin" if count == 1 else "covered")
        rows.append(ColorGapRow(family, count, status, recommendation, tuple(examples.get(family, [])[:3])))

    if counts.get("brown", 0) and not warm_brown:
        rows.append(ColorGapRow("warm_brown", 0, "missing_subtone", "add_warm_brown", ()))
    if counts.get("grey", 0) and not cool_grey:
        rows.append(ColorGapRow("cool_grey", 0, "missing_subtone", "add_cool_grey", ()))
    if counts.get("blue", 0) and not business_blue:
        rows.append(ColorGapRow("business_blue", 0, "missing_subtone", "add_business_blue", ()))

    order = {"missing": 0, "missing_subtone": 1, "thin": 2, "covered": 3}
    return sorted(rows, key=lambda r: (order.get(r.status, 9), r.family))


def nib_history_rows(pens: Iterable[Any], setups: Iterable[Any], *, reference: datetime | None = None) -> list[NibHistoryRow]:
    """Baut eine Feder-Tausch-Historie aus PenNibSetup-Einträgen."""
    reference = reference or datetime.now()
    pens_by_id = {getattr(p, "id", None): p for p in pens}
    rows: list[NibHistoryRow] = []
    for setup in setups:
        pen = getattr(setup, "pen", None) or pens_by_id.get(getattr(setup, "pen_id", None))
        nib = getattr(setup, "nib", None)
        installed = getattr(setup, "installed_date", None)
        removed = getattr(setup, "removed_date", None)
        active = bool(getattr(setup, "is_active", False)) and removed is None
        days = None
        if installed is not None:
            end = removed or reference
            days = max(0, (end - installed).days)
        notes = " | ".join(
            str(getattr(setup, f, "") or "").strip()
            for f in ("setup_label", "install_reason", "removal_reason", "compatibility_notes", "feel_notes")
            if str(getattr(setup, f, "") or "").strip()
        )
        rows.append(NibHistoryRow(
            pen_id=getattr(setup, "pen_id", None),
            pen_label=_pen_label(pen),
            nib_id=getattr(setup, "nib_id", None),
            nib_label=_nib_label(nib),
            installed_date=installed,
            removed_date=removed,
            active=active,
            days_installed=days,
            notes=notes,
        ))
    def _ts(value: datetime | None) -> float:
        return value.timestamp() if value else 0.0

    # Pro Füller zuerst das aktive Setup, danach die jüngsten früheren Setups.
    return sorted(rows, key=lambda r: (r.pen_label.lower(), not r.active, -_ts(r.installed_date)))


def cleaning_stats_rows(cleaning_logs: Iterable[Any], inks: Iterable[Any]) -> list[CleaningStatsRow]:
    """Aggregiert Reinigungsaufwand pro Tinte."""
    inks_by_id = {getattr(i, "id", None): i for i in inks}
    grouped: dict[int | None, list[Any]] = {}
    for log in cleaning_logs:
        grouped.setdefault(getattr(log, "ink_id", None), []).append(log)

    rows: list[CleaningStatsRow] = []
    for ink_id, logs in grouped.items():
        durations = [v for v in (_safe_float(getattr(l, "duration_minutes", None)) for l in logs) if v is not None]
        difficulties = [v for v in (_safe_int(getattr(l, "difficulty_level", None)) for l in logs) if v is not None]
        cycles = [v for v in (_safe_int(getattr(l, "flush_cycles", None)) for l in logs) if v is not None]
        last = max((getattr(l, "cleaned_at", None) for l in logs if getattr(l, "cleaned_at", None)), default=None)
        avg_diff = mean(difficulties) if difficulties else None
        avg_cycles = mean(cycles) if cycles else None
        status = "hard" if (
            (avg_diff is not None and avg_diff >= 4)
            or (durations and mean(durations) >= 20)
            or (avg_cycles is not None and avg_cycles >= 7)
        ) else "normal"
        rows.append(CleaningStatsRow(
            ink_id=ink_id,
            ink_label=_ink_label(inks_by_id.get(ink_id)) if ink_id else "—",
            cleanings=len(logs),
            avg_minutes=mean(durations) if durations else None,
            avg_difficulty=avg_diff,
            avg_flush_cycles=avg_cycles,
            last_cleaned_at=last,
            status=status,
        ))
    return sorted(rows, key=lambda r: (0 if r.status == "hard" else 1, r.ink_label.lower()))
