"""v0.3.01: Verhaltenstests für Dashboard-Service + Repository-Schicht.

Sichert die aus ``DashboardWidget.refresh()`` extrahierte Logik ab:
Wertberechnung mit Währungsumrechnung und Fehlwährungszählung,
Timer-Klassifikation (überfällig, bald fällig, critical-Grace),
Service-Sortierung, Aktivitätsformatierung, All-Clear-Bedingung und die
Repository-Delegation gegen eine Fake-Session.
"""
from __future__ import annotations

from datetime import datetime

# Importiert zuerst tests.conftest: aktiviert in der Sandbox den
# SQLAlchemy-Stub, bevor database/logic geladen werden (in der echten
# CI mit installiertem SQLAlchemy ist der Stub inaktiv, Import harmlos).
from tests.conftest import FakeInk as _StubHook  # noqa: F401

from database import repositories as repos
from logic import dashboard_service as ds


# ── Fake-ORM ────────────────────────────────────────────────────────────────

class Obj:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


class FakeQuery:
    def __init__(self, items):
        self._items = list(items)
    def filter_by(self, **kw):
        return FakeQuery([i for i in self._items
                          if all(getattr(i, k, None) == v for k, v in kw.items())])
    def order_by(self, *a):
        return self
    def limit(self, n):
        return FakeQuery(self._items[:n])
    def all(self):
        return list(self._items)
    def count(self):
        return len(self._items)


class FakeSession:
    def __init__(self, data):
        self._data = data
    def query(self, model):
        return FakeQuery(self._data.get(model.__name__, []))
    def get(self, model, oid):
        for item in self._data.get(model.__name__, []):
            if getattr(item, "id", None) == oid:
                return item
        return None


def _pen(i, **kw):
    base = dict(id=i, brand="B", model=f"P{i}", is_active=True,
                rotation_blocked=False, availability_status="available",
                current_ink_load=None, purchase_price=None,
                purchase_currency=None, current_market_value=None,
                market_currency=None, service_notes=None, blocked_until=None)
    base.update(kw)
    return Obj(**base)


def _ink(i, **kw):
    base = dict(id=i, brand="I", name=f"Ink{i}", is_archived=False,
                purchase_price=None, purchase_currency=None)
    base.update(kw)
    return Obj(**base)


def _load(pen_id, ink_id, days, loaded=None, cleaned=None):
    return Obj(pen_id=pen_id, ink_id=ink_id, days_loaded=days,
               loaded_date=loaded or datetime(2026, 7, 1), cleaned_date=cleaned)


IDENT = lambda amount, cur: float(amount)


# ── compute_collection_value ────────────────────────────────────────────────

def test_collection_value_prefers_market_and_counts_missing_currency():
    pens = [
        _pen(1, purchase_price=100, purchase_currency="CHF"),
        _pen(2, purchase_price=50, current_market_value=80, market_currency="EUR"),
        _pen(3, purchase_price=40),  # Betrag ohne Währung → missing
    ]
    inks = [_ink(1, purchase_price=20, purchase_currency="USD"),
            _ink(2, purchase_price=10)]  # missing
    total, currencies, missing = ds.compute_collection_value(pens, inks, IDENT, "CHF")
    assert total == 100 + 80 + 40 + 20 + 10
    assert currencies == {"CHF", "EUR", "USD"}
    assert missing == 2


def test_collection_value_converts_via_injected_function():
    double = lambda amount, cur: amount * 2
    total, _, _ = ds.compute_collection_value(
        [_pen(1, purchase_price=10, purchase_currency="EUR")], [], double, "CHF"
    )
    assert total == 20


# ── Timer-Klassifikation ────────────────────────────────────────────────────

def _timer_setup(days, max_days):
    ink = _ink(1)
    pen = _pen(1, current_ink_load=_load(1, 1, days))
    rows, extra, overdue = ds.build_timer_rows(
        [pen], get_ink=lambda i: ink, max_days_for=lambda p, i: max_days
    )
    return rows, extra, overdue


def test_timer_overdue_and_critical_grace():
    rows, extra, overdue = _timer_setup(days=20, max_days=14)
    assert overdue == 1 and rows[0]["overdue"] is True
    assert extra[0]["severity"] == "warning"          # 20 < 14+7
    _, extra2, _ = _timer_setup(days=21, max_days=14)
    assert extra2[0]["severity"] == "critical"        # 21 >= 14+7


def test_timer_visible_filter_soon_threshold():
    rows = [
        {"pen": "a", "ink": "x", "days": 5, "max": 28, "overdue": False},   # grün
        {"pen": "b", "ink": "x", "days": 23, "max": 28, "overdue": False},  # ≥80 %
        {"pen": "c", "ink": "x", "days": 30, "max": 28, "overdue": True},
    ]
    visible = ds.filter_visible_timer_rows(rows)
    assert [r["pen"] for r in visible] == ["b", "c"]


def test_timer_skips_pens_without_load_or_unknown_ink():
    pen_no_load = _pen(1)
    pen_ghost = _pen(2, current_ink_load=_load(2, 99, 5))
    rows, extra, overdue = ds.build_timer_rows(
        [pen_no_load, pen_ghost], get_ink=lambda i: None, max_days_for=lambda p, i: 28
    )
    assert rows == [] and extra == [] and overdue == 0


# ── Service-Zeilen ──────────────────────────────────────────────────────────

def test_block_service_rows_for_blocked_and_status():
    pens = [
        _pen(1, rotation_blocked=True),
        _pen(2, availability_status="service"),
        _pen(3),
    ]
    rows = ds.build_block_service_rows(pens)
    assert len(rows) == 2
    assert all(r["severity"] == "blocked" for r in rows)


def test_sort_service_rows_orders_by_severity():
    rows = [{"severity": "warning"}, {"severity": "critical"},
            {"severity": "blocked"}, {"severity": None}]
    ds.sort_service_rows(rows)
    assert [r["severity"] for r in rows] == ["critical", "blocked", "warning", None]


# ── Aktivität & Budget ──────────────────────────────────────────────────────

def test_activity_rows_and_last_activity():
    pen, ink = _pen(1), _ink(1)
    loads = [_load(1, 1, 3), _load(1, 1, 9, cleaned=datetime(2026, 7, 2))]
    rows, last = ds.build_activity_rows(
        loads, get_pen=lambda i: pen, get_ink=lambda i: ink
    )
    assert len(rows) == 2
    assert rows[0]["cleaned"] == "—"
    assert rows[1]["cleaned"] != "—"
    assert "B P1" in last


def test_summarize_budget_goals_completed_and_remaining():
    goals = [
        Obj(progress_percent=100, remaining_amount=0, currency="CHF"),
        Obj(progress_percent=40, remaining_amount=60, currency="CHF"),
        Obj(progress_percent=10, remaining_amount=-5, currency="CHF"),  # clamp
    ]
    completed, remaining_str = ds.summarize_budget_goals(goals, IDENT, "CHF")
    assert completed == 1
    assert "60" in remaining_str.replace("'", "").replace(" ", "")


# ── Orchestrierung (Fake-Session Ende-zu-Ende) ─────────────────────────────

def _full_session():
    ink = _ink(1, purchase_price=10, purchase_currency="CHF")
    pen_ok = _pen(1, purchase_price=100, purchase_currency="CHF",
                  current_ink_load=_load(1, 1, 30))  # überfällig bei max 14
    pen_blocked = _pen(2, rotation_blocked=True)
    return FakeSession({
        "Pen": [pen_ok, pen_blocked],
        "Ink": [ink],
        "Paper": [],
        "Expense": [],
        "InkLoad": [_load(1, 1, 30)],
    })


def test_collect_dashboard_data_end_to_end():
    data = ds.collect_dashboard_data(
        _full_session(),
        max_days_for=lambda p, i: 14,
        convert=IDENT,
        default_currency="CHF",
        budget_goals_loader=lambda: [],
        health_builder=lambda **kw: [],
    )
    assert data.pens_total == 2 and data.inks_total == 1
    assert data.timer_overdue == 1
    severities = [r["severity"] for r in data.service_rows]
    assert "blocked" in severities and "critical" in severities  # 30 ≥ 14+7
    assert data.service_rows[0]["severity"] == "critical"        # sortiert
    assert data.all_clear is False
    assert data.show_onboarding is False


def test_collect_dashboard_all_clear_when_inventory_clean():
    session = FakeSession({
        "Pen": [_pen(1, purchase_price=10, purchase_currency="CHF")],
        "Ink": [], "Paper": [], "Expense": [], "InkLoad": [],
    })
    data = ds.collect_dashboard_data(
        session, max_days_for=lambda p, i: 14, convert=IDENT,
        default_currency="CHF", budget_goals_loader=lambda: [],
        health_builder=lambda **kw: [],
    )
    assert data.all_clear is True


def test_collect_dashboard_budget_loader_failure_is_soft():
    def broken():
        raise OSError("BudgetManager-Datei fehlt")
    data = ds.collect_dashboard_data(
        _full_session(), max_days_for=lambda p, i: 14, convert=IDENT,
        default_currency="CHF", budget_goals_loader=broken,
        health_builder=lambda **kw: [],
    )
    assert data.budget_goals == []


# ── Repositories delegieren korrekt ────────────────────────────────────────

def test_repositories_filter_sort_and_limit():
    pens = [_pen(2, is_active=False), _pen(1)]
    inks = [_ink(1), _ink(2, is_archived=True)]
    loads = [_load(1, 1, 1) for _ in range(10)]
    session = FakeSession({"Pen": pens, "Ink": inks, "InkLoad": loads})
    assert len(repos.PenRepository(session).active()) == 1
    assert len(repos.PenRepository(session).all()) == 2
    assert repos.InkRepository(session).archived_count() == 1
    assert len(repos.InkRepository(session).active()) == 1
    assert len(repos.InkLoadRepository(session).recent(limit=3)) == 3
    assert repos.PenRepository(session).get(1).id == 1
    assert repos.PenRepository(session).get(999) is None
