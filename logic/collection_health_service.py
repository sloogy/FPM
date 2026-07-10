"""Sammlungs-Health/Advisor für Dashboard und Tests.

Die Logik ist bewusst UI-frei: Sie nimmt ORM-Objekte oder einfache Stubs und
liefert strukturierte Hinweise. Das Dashboard übersetzt die Codes in sichtbare
Texte. Ziel: Anfänger sehen klare nächste Schritte, Enthusiasten erhalten eine
Checkliste für Rotation, Wartung, Bestand und Werterfassung.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Callable, Iterable


@dataclass(frozen=True)
class HealthInsight:
    """Ein strukturierter Hinweis für die Sammlungsprüfung."""

    severity: str       # critical / warning / info
    area: str           # rotation / ink / paper / value / warranty / service
    code: str           # issue code, translated by UI
    entity: str
    detail: str = ""
    action: str = ""
    sort_score: int = 50


def _as_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def _name(obj: Any, kind: str = "item") -> str:
    if obj is None:
        return "—"
    if kind == "pen":
        return f"{getattr(obj, 'brand', '') or ''} {getattr(obj, 'model', '') or ''}".strip() or "—"
    if kind == "ink":
        return f"{getattr(obj, 'brand', '') or ''} {getattr(obj, 'name', '') or ''}".strip() or "—"
    if kind == "paper":
        return f"{getattr(obj, 'brand', '') or ''} {getattr(obj, 'name', '') or ''}".strip() or "—"
    return str(obj)


def _active_load_for_pen(pen: Any) -> Any | None:
    load = getattr(pen, "current_ink_load", None)
    if load is not None:
        return load
    for candidate in getattr(pen, "ink_loads", []) or []:
        if getattr(candidate, "cleaned_date", None) is None:
            return candidate
    return None


def _days_since(value: Any, today: date) -> int | None:
    d = _as_date(value)
    if d is None:
        return None
    return max(0, (today - d).days)


def _load_days(load: Any, today: date) -> int:
    direct = getattr(load, "days_loaded", None)
    if isinstance(direct, int):
        return max(0, direct)
    return _days_since(getattr(load, "loaded_date", None), today) or 0


def build_collection_health(
    *,
    pens: Iterable[Any] = (),
    inks: Iterable[Any] = (),
    papers: Iterable[Any] = (),
    expenses: Iterable[Any] = (),
    today: date | None = None,
    max_days_for_load: Callable[[Any, Any | None], int] | None = None,
    low_ink_ratio: float = 0.20,
    paper_low_ratio: float = 0.85,
    warranty_days: int = 45,
    limit: int = 12,
) -> list[HealthInsight]:
    """Erzeugt priorisierte Hinweise zur Sammlung.

    ``max_days_for_load`` bekommt ``(pen, ink)`` und kann z.B. die RuleEngine des
    Dashboards nutzen. Ohne Callback wird ``ink.max_days_in_pen`` oder 28 Tage
    verwendet. Die Funktion mutiert keine Daten und ist darum gut testbar.
    """
    today = today or date.today()
    insights: list[HealthInsight] = []

    active_pens = [p for p in pens if bool(getattr(p, "is_active", True))]
    active_ink_ids: set[int] = set()

    for pen in active_pens:
        status = (getattr(pen, "availability_status", None) or "available").lower()
        blocked = bool(getattr(pen, "rotation_blocked", False))
        pen_label = _name(pen, "pen")
        load = _active_load_for_pen(pen)

        if status != "available" or blocked:
            insights.append(HealthInsight(
                severity="warning",
                area="service",
                code="pen_blocked",
                entity=pen_label,
                detail=status,
                action="check_status",
                sort_score=18,
            ))
            continue

        if load is None:
            insights.append(HealthInsight(
                severity="info",
                area="rotation",
                code="empty_pen",
                entity=pen_label,
                detail=str(getattr(pen, "rotation_role", None) or "writer"),
                action="fill_or_rotate",
                sort_score=52,
            ))
        else:
            ink = getattr(load, "ink", None) or getattr(pen, "fixed_ink", None)
            ink_id = getattr(load, "ink_id", None) or getattr(ink, "id", None)
            if ink_id is not None:
                active_ink_ids.add(int(ink_id))
            days = _load_days(load, today)
            max_days = int(max_days_for_load(pen, ink) if max_days_for_load else (getattr(ink, "max_days_in_pen", None) or 28))
            if days > max_days:
                insights.append(HealthInsight(
                    severity="critical" if days >= max_days + 7 else "warning",
                    area="rotation",
                    code="load_overdue",
                    entity=pen_label,
                    detail=f"{days}/{max_days}",
                    action="clean_or_refill",
                    sort_score=5 if days >= max_days + 7 else 12,
                ))

        if not getattr(pen, "image_path", None) and (
            getattr(pen, "current_market_value", None) or getattr(pen, "insurance_value", None) or getattr(pen, "purchase_price", None)
        ):
            insights.append(HealthInsight(
                severity="info",
                area="value",
                code="missing_pen_photo",
                entity=pen_label,
                action="add_photo",
                sort_score=70,
            ))

        if not getattr(pen, "current_market_value", None) and not getattr(pen, "purchase_price", None):
            insights.append(HealthInsight(
                severity="info",
                area="value",
                code="missing_pen_value",
                entity=pen_label,
                action="add_value",
                sort_score=74,
            ))

    for ink in [i for i in inks if not bool(getattr(i, "is_archived", False))]:
        ink_label = _name(ink, "ink")
        remaining = getattr(ink, "remaining_ml", None)
        size = getattr(ink, "bottle_size_ml", None)
        is_empty = bool(getattr(ink, "is_empty", False)) or (remaining is not None and float(remaining or 0) <= 0)
        if is_empty:
            insights.append(HealthInsight(
                severity="warning",
                area="ink",
                code="ink_empty",
                entity=ink_label,
                action="archive_or_restock",
                sort_score=22,
            ))
        elif remaining is not None and size and float(size) > 0:
            ratio = float(remaining or 0) / float(size)
            if ratio <= low_ink_ratio:
                insights.append(HealthInsight(
                    severity="info",
                    area="ink",
                    code="ink_low",
                    entity=ink_label,
                    detail=f"{remaining:g}/{size:g} ml",
                    action="watch_or_restock",
                    sort_score=61,
                ))

        if getattr(ink, "id", None) in active_ink_ids and (
            bool(getattr(ink, "has_shimmer", False)) or bool(getattr(ink, "is_pigment", False)) or int(getattr(ink, "cleaning_effort", 3) or 3) >= 5
        ):
            insights.append(HealthInsight(
                severity="warning",
                area="ink",
                code="high_cleaning_active",
                entity=ink_label,
                action="plan_cleaning",
                sort_score=24,
            ))

    for paper in papers:
        total = getattr(paper, "pages_total", None)
        used = getattr(paper, "pages_used", None)
        if total and int(total) > 0 and used is not None:
            ratio = float(used or 0) / float(total)
            if ratio >= paper_low_ratio:
                insights.append(HealthInsight(
                    severity="info" if ratio < 0.95 else "warning",
                    area="paper",
                    code="paper_low",
                    entity=_name(paper, "paper"),
                    detail=f"{int(used)}/{int(total)}",
                    action="prepare_next_paper",
                    sort_score=64 if ratio < 0.95 else 32,
                ))

    horizon = today + timedelta(days=max(1, int(warranty_days)))
    for exp in expenses:
        warranty = _as_date(getattr(exp, "warranty_until", None))
        if warranty is None:
            continue
        if today <= warranty <= horizon:
            entity = getattr(exp, "linked_label", None) or getattr(exp, "description", None) or "—"
            days_left = max(0, (warranty - today).days)
            insights.append(HealthInsight(
                severity="warning" if days_left <= 14 else "info",
                area="warranty",
                code="warranty_expiring",
                entity=entity,
                detail=str(days_left),
                action="check_warranty",
                sort_score=15 if days_left <= 14 else 55,
            ))

    sev_order = {"critical": 0, "warning": 1, "info": 2}
    insights.sort(key=lambda row: (sev_order.get(row.severity, 9), row.sort_score, row.area, row.entity))
    return insights[: max(1, int(limit))]
