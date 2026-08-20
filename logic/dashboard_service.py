"""Dashboard-Service (Enterprise-Audit v0.3.00, P1: große Methoden/DB in UI).

Extrahiert die komplette Datenbeschaffung und -klassifikation aus der
309-Zeilen-Methode ``DashboardWidget.refresh()`` in reine, Qt-freie
Funktionen. Das Widget rendert nur noch; Zahlen, Sortierungen, Schwellwerte
und Texte entstehen hier und sind damit ohne GUI verhaltensgetestet
(``tests/test_dashboard_service_0301.py``).

Injektionspunkte statt harter Abhängigkeiten:
- ``max_days_for(pen, ink)``      → RuleEngine-Kapsel des Aufrufers
- ``convert(amount, currency)``   → LocaleService-Umrechnung
- ``budget_goals_loader()``       → BudgetManager-Brücke
- ``health_builder(...)``         → build_collection_health
- ``now``                          → Zeitquelle für deterministische Tests

Die Übersetzungsfunktion ``t`` sowie ``format_money``/``format_date`` sind
Qt-frei (etabliertes Muster der übrigen logic/-Services) und dürfen hier
verwendet werden, damit die bisherigen sichtbaren Texte 1:1 erhalten bleiben.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple

from database.repositories import (
    ExpenseRepository,
    InkLoadRepository,
    InkRepository,
    PaperRepository,
    PenRepository,
)
from i18n.translator import format_date, format_money, t

BLOCKING_STATUSES = {"problem", "service", "blocked", "dry_risk"}

# Ab diesem Anteil der Maximaltage gilt eine Ladung als "bald fällig"
# (v0.2.79: Dashboard ist Alarmzentrale, keine Inventarliste).
TIMER_SOON_RATIO = 0.8
# Ab so vielen Tagen Überzug wird der Service-Eintrag kritisch statt Warnung.
TIMER_CRITICAL_GRACE_DAYS = 7

_SEVERITY_ORDER = {"critical": 0, "blocked": 1, "warning": 2}


def _pen_name(pen: Any) -> str:
    return f"{getattr(pen, 'brand', '?')} {getattr(pen, 'model', '?')}".strip()


@dataclass
class DashboardData:
    """Vollständiges, render-fertiges Datenpaket für das Dashboard."""

    pens_total: int = 0
    inks_total: int = 0
    archived_total: int = 0
    active_loads_count: int = 0

    value_str: str = ""
    has_mixed_currencies: bool = False
    currencies_used: Set[str] = field(default_factory=set)
    missing_currency: int = 0

    budget_goals: List[Any] = field(default_factory=list)
    budget_completed: int = 0
    budget_remaining_str: str = ""

    timer_rows: List[Dict[str, Any]] = field(default_factory=list)
    timer_overdue: int = 0
    timer_due_soon: int = 0

    service_rows: List[Dict[str, Any]] = field(default_factory=list)
    service_critical: int = 0
    service_blocked: int = 0

    health_rows: List[Any] = field(default_factory=list)
    health_critical: int = 0
    health_warning: int = 0

    activity_rows: List[Dict[str, str]] = field(default_factory=list)
    last_activity: str = ""

    show_onboarding: bool = False
    all_clear: bool = False


# ── Reine Bausteine (einzeln getestet) ──────────────────────────────────────

def compute_collection_value(
    pens: Sequence[Any],
    inks: Sequence[Any],
    convert: Callable[[float, str], float],
    default_currency: str,
) -> Tuple[float, Set[str], int]:
    """Gesamtwert der Sammlung in Standardwährung.

    Marktwert hat Vorrang vor Kaufpreis; fehlende Währung bei vorhandenem
    Betrag wird gezählt und mit der Standardwährung angenähert.
    """
    currencies: Set[str] = set()
    total = 0.0
    missing = 0
    for p in pens:
        if getattr(p, "current_market_value", None):
            raw = p.current_market_value or 0
            cur = getattr(p, "market_currency", None) or getattr(p, "purchase_currency", None)
        else:
            raw = getattr(p, "purchase_price", None) or 0
            cur = getattr(p, "purchase_currency", None)
        if raw and not cur:
            missing += 1
            cur = default_currency
        cur = cur or default_currency
        currencies.add(cur)
        total += convert(raw, cur)
    for i in inks:
        raw = getattr(i, "purchase_price", None) or 0
        cur = getattr(i, "purchase_currency", None) or default_currency
        if raw and not getattr(i, "purchase_currency", None):
            missing += 1
        currencies.add(cur)
        total += convert(raw, cur)
    return total, currencies, missing


def build_block_service_rows(pens: Sequence[Any]) -> List[Dict[str, Any]]:
    """Zeilen für manuell gesperrte Füller bzw. blockierende Status."""
    rows: List[Dict[str, Any]] = []
    for pen in pens:
        status = getattr(pen, "availability_status", "available") or "available"
        if getattr(pen, "rotation_blocked", False) or status in BLOCKING_STATUSES:
            until = getattr(pen, "blocked_until", None)
            notes = getattr(pen, "service_notes", None) or t("ui.dashboard_widget.rotation_blocked")
            action = (
                t("ui.dashboard_widget.service_unlock_action")
                if status == "service"
                else t("ui.dashboard_widget.check_unlock_action")
            )
            rows.append({
                "pen": _pen_name(pen),
                "status": _status_label(status) or t("ui.dashboard_widget.blocked_status"),
                "reason": notes,
                "until": format_date(until) if until else t("ui.dashboard_widget.open_until"),
                "action": action,
                "severity": "blocked",
            })
    return rows


def _status_label(status: str) -> str:
    # 1:1 aus dem Widget übernommen (Key-Schema dashboard.status_labels.*)
    return t(f"dashboard.status_labels.{status}") if status else ""


def build_timer_rows(
    pens: Sequence[Any],
    get_ink: Callable[[int], Any],
    max_days_for: Callable[[Any, Any], int],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], int]:
    """Safety-Timer-Zeilen plus abgeleitete Service-Einträge für Überzieher.

    Rückgabe: (alle Timer-Zeilen, zusätzliche Service-Zeilen, Anzahl überfällig).
    """
    timer_rows: List[Dict[str, Any]] = []
    extra_service: List[Dict[str, Any]] = []
    overdue_count = 0
    for pen in pens:
        load = getattr(pen, "current_ink_load", None)
        if not load:
            continue
        ink = get_ink(load.ink_id)
        if not ink:
            continue
        max_days = max_days_for(pen, ink)
        days = load.days_loaded
        overdue = days > max_days
        if overdue:
            overdue_count += 1
        timer_rows.append({
            "pen": _pen_name(pen),
            "ink": f"{ink.brand} {ink.name}",
            "days": days,
            "max": max_days,
            "overdue": overdue,
        })
        if overdue:
            level = "critical" if days >= max_days + TIMER_CRITICAL_GRACE_DAYS else "warning"
            extra_service.append({
                "pen": _pen_name(pen),
                "status": t("ui.dashboard_widget.dry_risk_status"),
                "reason": t(
                    "ui.dashboard_widget.days_in_pen_reason",
                    ink=f"{ink.brand} {ink.name}", days=days, max_days=max_days,
                ),
                "until": t("ui.dashboard_widget.days_value", days=days),
                "action": t("ui.dashboard_widget.clean_or_change_action"),
                "severity": level,
            })
    timer_rows.sort(key=lambda r: r["overdue"], reverse=True)
    return timer_rows, extra_service, overdue_count


def filter_visible_timer_rows(
    timer_rows: Sequence[Dict[str, Any]],
    soon_ratio: float = TIMER_SOON_RATIO,
) -> List[Dict[str, Any]]:
    """Nur überfällige und bald fällige Ladungen (≥ soon_ratio·max)."""
    return [
        r for r in timer_rows
        if r["overdue"] or (r["max"] > 0 and r["days"] >= soon_ratio * r["max"])
    ]


def sort_service_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows.sort(key=lambda r: _SEVERITY_ORDER.get(r.get("severity"), 3))
    return rows


def build_activity_rows(
    loads: Sequence[Any],
    get_pen: Callable[[int], Any],
    get_ink: Callable[[int], Any],
) -> Tuple[List[Dict[str, str]], str]:
    rows: List[Dict[str, str]] = []
    last_activity = t("dashboard.tiles.activity.none")
    for idx, load in enumerate(loads):
        pen = get_pen(load.pen_id)
        ink = get_ink(load.ink_id)
        pen_txt = _pen_name(pen) if pen else "?"
        ink_txt = f"{ink.brand} {ink.name}" if ink else "?"
        loaded = format_date(load.loaded_date)
        cleaned = format_date(load.cleaned_date) if load.cleaned_date else "—"
        rows.append({"pen": pen_txt, "ink": ink_txt, "loaded": loaded, "cleaned": cleaned})
        if idx == 0:
            last_activity = f"{pen_txt} · {ink_txt} · {loaded}"
    return rows, last_activity


def summarize_budget_goals(
    goals: Sequence[Any],
    convert: Callable[[float, str], float],
    default_currency: str,
) -> Tuple[int, str]:
    completed = sum(1 for g in goals if g.progress_percent >= 100)
    remaining_total = sum(
        convert(max(0.0, g.remaining_amount), g.currency or default_currency)
        for g in goals
    )
    return completed, format_money(remaining_total)


# ── Orchestrierung ──────────────────────────────────────────────────────────

def collect_dashboard_data(
    session: Any,
    *,
    max_days_for: Callable[[Any, Any], int],
    convert: Callable[[float, str], float],
    default_currency: str,
    budget_goals_loader: Callable[[], List[Any]],
    health_builder: Callable[..., List[Any]],
    activity_limit: int = 8,
    health_limit: int = 6,
    now: Optional[datetime] = None,  # reserviert für zeitabhängige Erweiterungen
) -> DashboardData:
    """Sammelt alle Dashboard-Daten über die Repository-Schicht."""
    pen_repo = PenRepository(session)
    ink_repo = InkRepository(session)

    pens_all = pen_repo.all()
    pens = pen_repo.active()
    archived_pens = [p for p in pens_all if not getattr(p, "is_active", True)]
    inks = ink_repo.active()
    archived_inks = ink_repo.archived_count()
    papers = PaperRepository(session).all()
    expenses = ExpenseRepository(session).all()
    loads = InkLoadRepository(session).recent(activity_limit)

    data = DashboardData()
    data.pens_total = len(pens)
    data.inks_total = len(inks)
    data.archived_total = len(archived_pens) + archived_inks
    data.active_loads_count = len([
        p.current_ink_load for p in pens
        if p.current_ink_load
        and getattr(p, "availability_status", "available") == "available"
        and not getattr(p, "rotation_blocked", False)
    ])

    total_value, currencies, missing = compute_collection_value(
        pens, inks, convert, default_currency
    )
    data.currencies_used = currencies
    data.missing_currency = missing
    data.has_mixed_currencies = len(currencies) > 1
    data.value_str = format_money(total_value) + (" ~" if data.has_mixed_currencies else "")

    data.show_onboarding = data.pens_total == 0 and data.inks_total == 0

    try:
        data.budget_goals = list(budget_goals_loader() or [])
    except (OSError, ValueError, KeyError, AttributeError, TypeError):
        # Externe BudgetManager-Datei fehlt/defekt → Kachel bleibt einfach aus.
        data.budget_goals = []
    if data.budget_goals:
        data.budget_completed, data.budget_remaining_str = summarize_budget_goals(
            data.budget_goals, convert, default_currency
        )

    service_rows = build_block_service_rows(pens)
    timer_rows, extra_service, overdue = build_timer_rows(
        pens, ink_repo.get, max_days_for
    )
    service_rows.extend(extra_service)
    data.timer_rows = filter_visible_timer_rows(timer_rows)
    data.timer_overdue = overdue
    data.timer_due_soon = sum(1 for r in data.timer_rows if not r["overdue"])

    sort_service_rows(service_rows)
    data.service_rows = service_rows
    data.service_critical = sum(1 for r in service_rows if r.get("severity") == "critical")
    data.service_blocked = sum(1 for r in service_rows if r.get("severity") == "blocked")

    data.health_rows = health_builder(
        pens=pens, inks=inks, papers=papers, expenses=expenses,
        max_days_for_load=max_days_for, limit=health_limit,
    )
    data.health_critical = sum(1 for h in data.health_rows if h.severity == "critical")
    data.health_warning = sum(1 for h in data.health_rows if h.severity == "warning")

    data.activity_rows, data.last_activity = build_activity_rows(
        loads, pen_repo.get, ink_repo.get
    )

    has_inventory = bool(pens or inks)
    data.all_clear = has_inventory and not service_rows and not data.health_rows and overdue == 0
    return data
