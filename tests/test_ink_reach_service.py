"""Tests für Tintenreichweite & Kosten-Effizienz (reine Logik, DB-frei)."""
from datetime import date, datetime, timedelta

from logic.ink_reach_service import (
    ink_reach_row,
    ink_reach_rows,
    collection_ink_value_summary,
)


class FakeLoad:
    def __init__(self, volume_ml=None, loaded_date=None):
        self.volume_ml = volume_ml
        self.loaded_date = loaded_date


class FakeInk:
    def __init__(self, **kw):
        self.id = kw.get("id", 1)
        self.brand = kw.get("brand", "TestBrand")
        self.name = kw.get("name", "TestInk")
        self.remaining_ml = kw.get("remaining_ml", None)
        self.bottle_size_ml = kw.get("bottle_size_ml", None)
        self.purchase_price = kw.get("purchase_price", None)
        self.purchase_currency = kw.get("purchase_currency", None)
        self.is_empty = kw.get("is_empty", False)
        self.is_archived = kw.get("is_archived", False)
        self.ink_loads = kw.get("ink_loads", [])


REF = date(2026, 7, 1)


# ── Grundfälle ────────────────────────────────────────────────────
def test_no_data_is_insufficient():
    row = ink_reach_row(FakeInk(remaining_ml=None), reference=REF)
    assert row.status == "insufficient_data"
    assert row.avg_fill_ml is None
    assert row.days_left is None


def test_recorded_fills_and_average():
    ink = FakeInk(
        remaining_ml=30.0, bottle_size_ml=50.0,
        ink_loads=[FakeLoad(1.0, datetime(2026, 1, 1)),
                   FakeLoad(1.5, datetime(2026, 3, 1)),
                   FakeLoad(0, datetime(2026, 3, 2)),        # 0-Vol ignoriert
                   FakeLoad(None, datetime(2026, 4, 1))],    # None ignoriert
    )
    row = ink_reach_row(ink, reference=REF)
    assert row.recorded_fills == 2
    assert row.total_consumed_ml == 2.5
    assert row.avg_fill_ml == 1.25


def test_estimated_fills_left():
    ink = FakeInk(
        remaining_ml=10.0,
        ink_loads=[FakeLoad(2.0, datetime(2026, 1, 1)),
                   FakeLoad(2.0, datetime(2026, 2, 1))],
    )
    row = ink_reach_row(ink, reference=REF)
    # avg 2.0 → 10 / 2 = 5 Füllungen
    assert row.estimated_fills_left == 5.0


# ── Verbrauchsrate / Leerdatum ────────────────────────────────────
def test_consumption_rate_and_projection():
    # 6 ml über genau 60 Tage → 0.1 ml/Tag; Rest 3 ml → 30 Tage
    start = REF - timedelta(days=60)
    mid = REF - timedelta(days=30)
    ink = FakeInk(
        remaining_ml=3.0,
        ink_loads=[FakeLoad(3.0, start), FakeLoad(3.0, mid)],
    )
    row = ink_reach_row(ink, reference=REF)
    assert row.daily_ml == 0.1
    assert row.days_left == 30
    assert row.projected_empty == REF + timedelta(days=30)
    assert row.status == "reorder_soon"  # <= 45 Tage


def test_rate_suppressed_for_short_window():
    ink = FakeInk(
        remaining_ml=40.0,
        ink_loads=[FakeLoad(1.0, REF - timedelta(days=3))],
    )
    row = ink_reach_row(ink, reference=REF)
    assert row.daily_ml is None
    assert row.days_left is None


# ── Kosten-/Wert-Sicht ────────────────────────────────────────────
def test_cost_metrics():
    ink = FakeInk(
        remaining_ml=25.0, bottle_size_ml=50.0,
        purchase_price=20.0, purchase_currency="CHF",
        ink_loads=[FakeLoad(2.0, datetime(2026, 1, 1)),
                   FakeLoad(2.0, datetime(2026, 2, 1))],
    )
    row = ink_reach_row(ink, reference=REF)
    assert row.cost_per_ml == 0.4          # 20 / 50
    assert row.cost_per_fill == 0.8        # 0.4 * 2.0
    assert row.value_used == 1.6           # 0.4 * 4.0
    assert row.value_remaining == 10.0     # 0.4 * 25
    assert row.currency == "CHF"


def test_cost_none_without_price_or_size():
    ink = FakeInk(remaining_ml=10.0, bottle_size_ml=None, purchase_price=20.0)
    row = ink_reach_row(ink, reference=REF)
    assert row.cost_per_ml is None
    assert row.cost_per_fill is None


# ── Status / Sortierung ───────────────────────────────────────────
def test_empty_ink_reorder_soon():
    row = ink_reach_row(FakeInk(is_empty=True, remaining_ml=0.0), reference=REF)
    assert row.status == "reorder_soon"


def test_rows_sorted_by_urgency_and_skip_archived():
    healthy = FakeInk(id=1, name="Healthy", remaining_ml=45.0, bottle_size_ml=50.0,
                      ink_loads=[FakeLoad(1.0, REF - timedelta(days=200))])
    urgent = FakeInk(id=2, name="Urgent", is_empty=True, remaining_ml=0.0)
    archived = FakeInk(id=3, name="Archived", is_archived=True, remaining_ml=0.0, is_empty=True)
    rows = ink_reach_rows([healthy, urgent, archived], reference=REF)
    assert [r.ink_id for r in rows] == [2, 1]  # archived rausgefiltert, urgent zuerst


# ── Aggregat (Sammler) ────────────────────────────────────────────
def test_collection_value_summary_single_currency():
    a = FakeInk(id=1, name="A", remaining_ml=25.0, bottle_size_ml=50.0,
                purchase_price=10.0, purchase_currency="CHF",
                ink_loads=[FakeLoad(5.0, datetime(2026, 1, 1))])
    b = FakeInk(id=2, name="B", remaining_ml=10.0, bottle_size_ml=30.0,
                purchase_price=30.0, purchase_currency="CHF",
                ink_loads=[FakeLoad(2.0, datetime(2026, 1, 1))])
    summary = collection_ink_value_summary([a, b], reference=REF)
    assert summary["currency"] == "CHF"
    assert summary["inks_evaluated"] == 2
    # a: 0.2/ml, b: 1.0/ml → a wirtschaftlicher
    assert summary["most_economical"].ink_id == 1
    assert summary["least_economical"].ink_id == 2


def test_collection_value_summary_mixed_currency():
    a = FakeInk(id=1, purchase_price=10.0, bottle_size_ml=50.0, purchase_currency="CHF",
                remaining_ml=10.0, ink_loads=[FakeLoad(1.0, datetime(2026, 1, 1))])
    b = FakeInk(id=2, purchase_price=10.0, bottle_size_ml=50.0, purchase_currency="EUR",
                remaining_ml=10.0, ink_loads=[FakeLoad(1.0, datetime(2026, 1, 1))])
    summary = collection_ink_value_summary([a, b], reference=REF)
    assert summary["currency"] == "mixed"
