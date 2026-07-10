"""Reine Statistik-Helfer für Ausgaben und Nutzung.

Die Funktionen arbeiten bewusst mit ``getattr`` statt festen SQLAlchemy-Typen.
So bleiben sie leicht testbar und können mit bereits geladenen ORM-Objekten,
Stubs oder späteren Importformaten genutzt werden.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Callable, Iterable, Any

DateLike = date | datetime | None


def _as_date(value: DateLike) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def period_bounds(period: str, reference: DateLike | None = None) -> tuple[date | None, date | None]:
    """Gibt einen halb-offenen Datumsbereich zurück: ``start <= d < end``.

    ``overall`` liefert ``(None, None)``. ``week`` nutzt ISO-Wochen mit Montag
    als Start. ``month`` und ``year`` orientieren sich an ``reference``.
    """
    p = (period or "overall").lower()
    ref = _as_date(reference) or date.today()
    if p == "overall":
        return None, None
    if p == "week":
        start = ref - timedelta(days=ref.weekday())
        return start, start + timedelta(days=7)
    if p == "month":
        start = date(ref.year, ref.month, 1)
        if ref.month == 12:
            end = date(ref.year + 1, 1, 1)
        else:
            end = date(ref.year, ref.month + 1, 1)
        return start, end
    if p == "year":
        return date(ref.year, 1, 1), date(ref.year + 1, 1, 1)
    return None, None


def in_period(value: DateLike, start: date | None, end: date | None) -> bool:
    d = _as_date(value)
    if d is None:
        return start is None and end is None
    if start is not None and d < start:
        return False
    if end is not None and d >= end:
        return False
    return True


def period_label(period: str, reference: DateLike | None = None) -> str:
    """Technisches Periodenlabel für Tests/Debug. UI übersetzt separat."""
    start, end = period_bounds(period, reference)
    if start is None or end is None:
        return "overall"
    return f"{start.isoformat()}..{(end - timedelta(days=1)).isoformat()}"


def summarize_expenses(
    expenses: Iterable[Any],
    *,
    period: str = "overall",
    reference: DateLike | None = None,
    item_types: set[str] | None = None,
    convert_to_default: Callable[[float, str], float] | None = None,
) -> dict[str, Any]:
    """Summiert Ausgaben für den gewählten Zeitraum und Typfilter."""
    start, end = period_bounds(period, reference)
    by_type: dict[str, dict[str, Any]] = {}
    by_currency: dict[str, float] = defaultdict(float)
    total_default = 0.0
    count = 0

    for exp in expenses:
        if not in_period(getattr(exp, "purchase_date", None), start, end):
            continue
        item_type = getattr(exp, "item_type", None) or "other"
        if item_types and item_type not in item_types:
            continue
        currency = getattr(exp, "currency", None) or "CHF"
        amount = float(getattr(exp, "total", 0.0) or 0.0)
        converted = convert_to_default(amount, currency) if convert_to_default else amount

        count += 1
        total_default += converted
        by_currency[currency] += amount
        bucket = by_type.setdefault(item_type, {
            "item_type": item_type,
            "count": 0,
            "total_default": 0.0,
            "by_currency": defaultdict(float),
        })
        bucket["count"] += 1
        bucket["total_default"] += converted
        bucket["by_currency"][currency] += amount

    for bucket in by_type.values():
        bucket["by_currency"] = dict(bucket["by_currency"])

    return {
        "count": count,
        "total_default": total_default,
        "average_default": (total_default / count) if count else 0.0,
        "by_currency": dict(by_currency),
        "by_type": by_type,
        "start": start,
        "end": end,
    }


def _label_for_entity(entity: Any, kind: str) -> str:
    if entity is None:
        return "—"
    if kind == "pen":
        return f"{getattr(entity, 'brand', '') or ''} {getattr(entity, 'model', '') or ''}".strip() or "—"
    if kind == "ink":
        return f"{getattr(entity, 'brand', '') or ''} {getattr(entity, 'name', '') or ''}".strip() or "—"
    return str(entity)


def _inclusive_overlap_days(
    loaded: DateLike,
    cleaned: DateLike,
    *,
    start: date | None,
    end: date | None,
    today: date | None = None,
) -> int:
    load_start = _as_date(loaded)
    if load_start is None:
        return 0
    current_day = today or date.today()
    load_end = _as_date(cleaned) or current_day

    # Füllungen am selben Tag sollen als ein Nutzungstag zählen.
    left = load_start if start is None else max(load_start, start)
    right_limit = load_end if end is None else min(load_end, end - timedelta(days=1))
    if right_limit < left:
        return 0
    return (right_limit - left).days + 1


def rank_usage(
    ink_loads: Iterable[Any],
    *,
    kind: str,
    period: str = "overall",
    reference: DateLike | None = None,
    today: date | None = None,
) -> list[dict[str, Any]]:
    """Rangliste meistgenutzter Füller oder Tinten aus InkLoad-Historie.

    Sortiert wird nach Nutzungstagen im gewählten Zeitraum, danach nach Anzahl
    Befüllungen, danach nach Gesamtvolumen. Das ist robuster als reine Counts,
    weil eine über den Monatswechsel aktive Füllung im neuen Monat weiter zählt.
    """
    if kind not in {"pen", "ink"}:
        raise ValueError("kind must be 'pen' or 'ink'")

    start, end = period_bounds(period, reference)
    buckets: dict[int, dict[str, Any]] = {}

    for load in ink_loads:
        entity = getattr(load, kind, None)
        entity_id = getattr(entity, "id", None) or getattr(load, f"{kind}_id", None)
        if entity_id is None:
            continue

        days = _inclusive_overlap_days(
            getattr(load, "loaded_date", None),
            getattr(load, "cleaned_date", None),
            start=start,
            end=end,
            today=today,
        )
        loaded_in_period = in_period(getattr(load, "loaded_date", None), start, end)
        if days <= 0 and not loaded_in_period:
            continue

        bucket = buckets.setdefault(int(entity_id), {
            "id": int(entity_id),
            "label": _label_for_entity(entity, kind),
            "fill_count": 0,
            "usage_days": 0,
            "volume_ml": 0.0,
            "last_loaded": None,
        })
        if loaded_in_period:
            bucket["fill_count"] += 1
        bucket["usage_days"] += days
        bucket["volume_ml"] += float(getattr(load, "volume_ml", 0.0) or 0.0)
        loaded_date = _as_date(getattr(load, "loaded_date", None))
        if loaded_date and (bucket["last_loaded"] is None or loaded_date > bucket["last_loaded"]):
            bucket["last_loaded"] = loaded_date

    return sorted(
        buckets.values(),
        key=lambda r: (r["usage_days"], r["fill_count"], r["volume_ml"], r["label"]),
        reverse=True,
    )

# ---------------------------------------------------------------------------
# Collector Insights (v0.2.57): Sammlungswert, Budget, Nutzungs-Staleness
# ---------------------------------------------------------------------------

def collection_value_summary(pens: Iterable[Any], convert: Any = None) -> dict:
    """Sammlungswert über aktive Füller: Kauf-, Markt- und Versicherungswert.

    ``convert(amount, currency)`` kann Beträge in die Standardwährung
    umrechnen; ohne Callable werden Rohbeträge summiert. Delta bezieht sich
    nur auf Füller, die BEIDE Werte (Kauf + Markt) besitzen, damit fehlende
    Marktwerte keine scheinbaren Verluste erzeugen.
    """
    def _conv(amount: float, currency: str | None) -> float:
        if convert is None:
            return float(amount)
        return float(convert(amount, currency))

    purchase_total = market_total = insurance_total = 0.0
    paired_purchase = paired_market = 0.0
    counted = valued = 0
    for pen in pens:
        if getattr(pen, "is_active", True) is False:
            continue
        counted += 1
        p = getattr(pen, "purchase_price", None)
        m = getattr(pen, "current_market_value", None)
        i = getattr(pen, "insurance_value", None)
        p_cur = getattr(pen, "purchase_currency", None)
        m_cur = getattr(pen, "market_currency", None) or p_cur
        i_cur = getattr(pen, "insurance_currency", None) or p_cur
        if p:
            purchase_total += _conv(p, p_cur)
        if m:
            market_total += _conv(m, m_cur)
            valued += 1
        if i:
            insurance_total += _conv(i, i_cur)
        if p and m:
            paired_purchase += _conv(p, p_cur)
            paired_market += _conv(m, m_cur)
    delta = paired_market - paired_purchase
    delta_pct = (delta / paired_purchase * 100.0) if paired_purchase > 0 else None
    return {
        "counted": counted,
        "valued": valued,
        "purchase_total": purchase_total,
        "market_total": market_total,
        "insurance_total": insurance_total,
        "delta": delta,
        "delta_pct": delta_pct,
    }


def value_by_year(pens: Iterable[Any], convert: Any = None) -> list[dict]:
    """Wertentwicklung: Kaufsummen pro Jahr plus kumulierte Summe."""
    def _conv(amount: float, currency: str | None) -> float:
        if convert is None:
            return float(amount)
        return float(convert(amount, currency))

    per_year: dict[int, dict] = {}
    for pen in pens:
        if getattr(pen, "is_active", True) is False:
            continue
        d = _as_date(getattr(pen, "purchase_date", None))
        price = getattr(pen, "purchase_price", None)
        if d is None:
            continue
        row = per_year.setdefault(d.year, {"year": d.year, "count": 0, "purchase_total": 0.0})
        row["count"] += 1
        if price:
            row["purchase_total"] += _conv(price, getattr(pen, "purchase_currency", None))
    rows = [per_year[y] for y in sorted(per_year)]
    cumulative = 0.0
    for row in rows:
        cumulative += row["purchase_total"]
        row["cumulative_total"] = cumulative
    return rows


def budget_status(spent: float, budget: float) -> dict:
    """Budgetampel: none (kein Budget), ok (<80%), warn (80–100%), over (>100%)."""
    if not budget or budget <= 0:
        return {"budget": 0.0, "spent": float(spent), "remaining": None, "pct": None, "level": "none"}
    pct = spent / budget * 100.0
    if pct > 100.0:
        level = "over"
    elif pct >= 80.0:
        level = "warn"
    else:
        level = "ok"
    return {"budget": float(budget), "spent": float(spent), "remaining": budget - spent, "pct": pct, "level": level}


def stale_ranking(entities: Iterable[Any], loads: Iterable[Any], kind: str,
                  reference: DateLike | None = None, limit: int | None = None) -> list[dict]:
    """Füller/Tinten sortiert nach "am längsten ungenutzt".

    Letzte Nutzung = jüngstes loaded_date/cleaned_date der zugehörigen
    InkLoads. Nie benutzte Objekte stehen ganz oben (days=None, never=True).
    ``kind`` ist "pen" oder "ink".
    """
    ref = _as_date(reference) or date.today()
    id_attr = "pen_id" if kind == "pen" else "ink_id"
    last_used: dict[int, date] = {}
    for load in loads:
        key = getattr(load, id_attr, None)
        if key is None:
            continue
        for attr in ("loaded_date", "cleaned_date"):
            d = _as_date(getattr(load, attr, None))
            if d and (key not in last_used or d > last_used[key]):
                last_used[key] = d
    rows: list[dict] = []
    for entity in entities:
        if getattr(entity, "is_active", True) is False or getattr(entity, "is_archived", False):
            continue
        eid = getattr(entity, "id", None)
        last = last_used.get(eid)
        rows.append({
            "id": eid,
            "label": _label_for_entity(entity, kind),
            "days": (ref - last).days if last else None,
            "never": last is None,
        })
    rows.sort(key=lambda r: (0 if r["never"] else 1, -(r["days"] or 0)))
    return rows[:limit] if limit else rows


def build_insurance_rows(pens: Iterable[Any]) -> list[list[str]]:
    """CSV-Zeilen für eine Versicherungsliste der aktiven Sammlung."""
    header = ["Marke", "Modell", "Farbe", "Kaufdatum", "Kaufpreis", "Währung",
              "Marktwert", "Versicherungswert", "Tags"]
    rows = [header]
    for pen in pens:
        if getattr(pen, "is_active", True) is False:
            continue
        d = _as_date(getattr(pen, "purchase_date", None))
        rows.append([
            str(getattr(pen, "brand", "") or ""),
            str(getattr(pen, "model", "") or ""),
            str(getattr(pen, "color", "") or ""),
            d.isoformat() if d else "",
            f"{getattr(pen, 'purchase_price', 0) or 0:.2f}",
            str(getattr(pen, "purchase_currency", "") or ""),
            f"{getattr(pen, 'current_market_value', 0) or 0:.2f}",
            f"{getattr(pen, 'insurance_value', 0) or 0:.2f}",
            str(getattr(pen, "tags", "") or ""),
        ])
    return rows


def build_statistics_csv_rows(expense_stats: dict, pen_rank: list, ink_rank: list,
                              value_summary: dict) -> list[list[str]]:
    """Exportierbare Zeilen der aktuellen Statistik-Ansicht (sprachneutral roh)."""
    rows: list[list[str]] = [["Sektion", "Feld", "Wert"]]
    rows.append(["Ausgaben", "Summe", f"{expense_stats.get('total_default', 0):.2f}"])
    rows.append(["Ausgaben", "Anzahl", str(expense_stats.get("count", 0))])
    for entry in expense_stats.get("by_type", {}).values():
        rows.append(["Ausgaben je Kategorie", str(entry.get("item_type", "")), f"{entry.get('total_default', 0):.2f}"])
    for r in pen_rank:
        rows.append(["Meistgenutzte Füller", str(r.get("label", "")), str(r.get("days", r.get("value", "")))])
    for r in ink_rank:
        rows.append(["Meistgenutzte Tinten", str(r.get("label", "")), str(r.get("days", r.get("value", "")))])
    rows.append(["Sammlungswert", "Kaufwert", f"{value_summary.get('purchase_total', 0):.2f}"])
    rows.append(["Sammlungswert", "Marktwert", f"{value_summary.get('market_total', 0):.2f}"])
    rows.append(["Sammlungswert", "Versicherungswert", f"{value_summary.get('insurance_total', 0):.2f}"])
    rows.append(["Sammlungswert", "Wertänderung", f"{value_summary.get('delta', 0):.2f}"])
    return rows
