"""Tintenreichweite & Kosten-Effizienz (v0.2.68).

Diese Auswertung verdichtet die vorhandene Füll-Historie (``InkLoad``) einer
Tinte zu zwei Sichten:

* Enthusiast-Sicht: geschätzte verbleibende Füllungen, Verbrauchsrate pro Tag,
  voraussichtliches Leerdatum. Beantwortet „Wie lange reicht die Flasche noch?"
* Sammler-Sicht: Kosten pro Milliliter, Kosten pro Füllung und der bereits
  verbrauchte Geldwert. Beantwortet „Wie wirtschaftlich ist diese Flasche?"

Design-Prinzipien (bewusst wie die übrigen ``logic``-Services):

* Reine Logik ohne SQLAlchemy-Import – dadurch testbar ohne DB/GUI-Runtime.
* Keine Mutation der übergebenen Objekte.
* Unvollständige Daten führen nie zu Fehlern, sondern zu ``None`` und dem
  Status ``insufficient_data``. Fehlende Werte werden nicht geraten.
* Es wird kein Verbrauch geschätzt, der nicht real erfasst wurde: Grundlage
  sind ausschließlich ``InkLoad``-Einträge mit einem positiven ``volume_ml``.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Iterable

# Ab dieser Beobachtungsspanne (Tage) gilt eine Verbrauchsrate als belastbar.
# Darunter ist die Hochrechnung auf ein Leerdatum zu wackelig und wird
# bewusst unterdrückt, statt eine Scheingenauigkeit zu erzeugen.
_MIN_RATE_WINDOW_DAYS = 14

# Ab so wenig Restreichweite wird zum Nachkauf geraten.
_REORDER_DAYS = 45
_REORDER_FILLS = 1.0


@dataclass(frozen=True)
class InkReachRow:
    ink_id: Any
    label: str
    remaining_ml: float | None
    bottle_size_ml: float | None
    recorded_fills: int
    total_consumed_ml: float
    avg_fill_ml: float | None
    estimated_fills_left: float | None
    daily_ml: float | None
    days_left: int | None
    projected_empty: date | None
    cost_per_ml: float | None
    cost_per_fill: float | None
    value_used: float | None
    value_remaining: float | None
    currency: str | None
    status: str  # insufficient_data | reorder_soon | healthy


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def _ink_label(ink: Any) -> str:
    brand = str(getattr(ink, "brand", "") or "").strip()
    name = str(getattr(ink, "name", "") or "").strip()
    label = " ".join(part for part in (brand, name) if part)
    return label or "—"


def _iter_loads(ink: Any) -> list[Any]:
    loads = getattr(ink, "ink_loads", None) or []
    try:
        return list(loads)
    except TypeError:
        return []


def ink_reach_row(ink: Any, *, reference: date | None = None) -> InkReachRow:
    """Berechnet die Reichweite- und Kostensicht für genau eine Tinte."""
    today = reference or date.today()

    remaining = _safe_float(getattr(ink, "remaining_ml", None))
    size = _safe_float(getattr(ink, "bottle_size_ml", None))
    price = _safe_float(getattr(ink, "purchase_price", None))
    currency = getattr(ink, "purchase_currency", None) or None

    # Reale, erfasste Füllungen mit positivem Volumen.
    fills: list[tuple[date | None, float]] = []
    for load in _iter_loads(ink):
        vol = _safe_float(getattr(load, "volume_ml", None))
        if vol is None or vol <= 0:
            continue
        fills.append((_as_date(getattr(load, "loaded_date", None)), vol))

    recorded_fills = len(fills)
    total_consumed = round(sum(v for _d, v in fills), 3)
    avg_fill = round(total_consumed / recorded_fills, 3) if recorded_fills else None

    # Verbleibende Füllungen aus Rest / Durchschnittsfüllung.
    estimated_fills_left = None
    if remaining is not None and avg_fill and avg_fill > 0:
        estimated_fills_left = round(remaining / avg_fill, 1)

    # Verbrauchsrate pro Tag über das beobachtete Fenster.
    daily_ml = None
    days_left = None
    projected_empty = None
    dated = sorted(d for d, _v in fills if d is not None)
    if dated:
        span_days = (today - dated[0]).days
        if span_days >= _MIN_RATE_WINDOW_DAYS and total_consumed > 0:
            daily_ml = round(total_consumed / span_days, 4)
            if remaining is not None and daily_ml > 0:
                days_left = int(remaining / daily_ml)
                projected_empty = today + timedelta(days=days_left)

    # Kosten-/Wert-Sicht (Sammler).
    cost_per_ml = None
    if price is not None and size and size > 0:
        cost_per_ml = round(price / size, 4)
    cost_per_fill = round(cost_per_ml * avg_fill, 3) if (cost_per_ml is not None and avg_fill) else None
    value_used = round(cost_per_ml * total_consumed, 2) if (cost_per_ml is not None and total_consumed) else None
    value_remaining = round(cost_per_ml * remaining, 2) if (cost_per_ml is not None and remaining is not None) else None

    # Status.
    is_empty = bool(getattr(ink, "is_empty", False)) or (remaining is not None and remaining <= 0)
    if is_empty:
        status = "reorder_soon"
    elif remaining is None or recorded_fills == 0:
        status = "insufficient_data"
    elif (days_left is not None and days_left <= _REORDER_DAYS) or (
        estimated_fills_left is not None and estimated_fills_left <= _REORDER_FILLS
    ):
        status = "reorder_soon"
    else:
        status = "healthy"

    return InkReachRow(
        ink_id=getattr(ink, "id", None),
        label=_ink_label(ink),
        remaining_ml=remaining,
        bottle_size_ml=size,
        recorded_fills=recorded_fills,
        total_consumed_ml=total_consumed,
        avg_fill_ml=avg_fill,
        estimated_fills_left=estimated_fills_left,
        daily_ml=daily_ml,
        days_left=days_left,
        projected_empty=projected_empty,
        cost_per_ml=cost_per_ml,
        cost_per_fill=cost_per_fill,
        value_used=value_used,
        value_remaining=value_remaining,
        currency=currency,
        status=status,
    )


def ink_reach_rows(inks: Iterable[Any], *, reference: date | None = None,
                   include_archived: bool = False) -> list[InkReachRow]:
    """Reichweite-/Kostenzeilen für viele Tinten, sortiert nach Dringlichkeit."""
    rows: list[InkReachRow] = []
    for ink in inks:
        if not include_archived and bool(getattr(ink, "is_archived", False)):
            continue
        rows.append(ink_reach_row(ink, reference=reference))

    severity = {"reorder_soon": 0, "healthy": 1, "insufficient_data": 2}

    def _key(r: InkReachRow):
        # Innerhalb "reorder_soon" zuerst die mit den wenigsten Resttagen.
        days_key = r.days_left if r.days_left is not None else 10_000
        return (severity.get(r.status, 9), days_key, r.label.lower())

    return sorted(rows, key=_key)


def collection_ink_value_summary(inks: Iterable[Any], *,
                                 reference: date | None = None) -> dict[str, Any]:
    """Aggregierte Sammler-Sicht über alle Tinten.

    Liefert verbrauchten und verbleibenden Geldwert sowie die wirtschaftlichste
    und teuerste Tinte (Kosten pro ml). Währungen werden nicht umgerechnet;
    gemischte Währungen werden als ``mixed`` gemeldet, damit keine falsch
    summierten Beträge entstehen.
    """
    rows = ink_reach_rows(inks, reference=reference)
    currencies = {r.currency for r in rows if r.currency}
    currency = currencies.pop() if len(currencies) == 1 else ("mixed" if currencies else None)

    value_used = round(sum(r.value_used or 0.0 for r in rows), 2)
    value_remaining = round(sum(r.value_remaining or 0.0 for r in rows), 2)
    total_consumed_ml = round(sum(r.total_consumed_ml for r in rows), 2)

    priced = [r for r in rows if r.cost_per_ml is not None]
    most_economical = min(priced, key=lambda r: r.cost_per_ml, default=None)
    least_economical = max(priced, key=lambda r: r.cost_per_ml, default=None)
    reorder_soon = [r for r in rows if r.status == "reorder_soon"]

    return {
        "inks_evaluated": len(rows),
        "currency": currency,
        "value_used": value_used,
        "value_remaining": value_remaining,
        "total_consumed_ml": total_consumed_ml,
        "reorder_soon_count": len(reorder_soon),
        "most_economical": most_economical,
        "least_economical": least_economical,
    }
