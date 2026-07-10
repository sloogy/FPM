"""Tests für die Collector-Insights-Logik (v0.2.57).

Pure-Logic-Tests ohne DB/GUI: collection_value_summary, value_by_year,
budget_status, stale_ranking, build_insurance_rows, build_statistics_csv_rows.
"""
from datetime import date
from types import SimpleNamespace as NS

from logic.statistics_service import (
    collection_value_summary,
    value_by_year,
    budget_status,
    stale_ranking,
    build_insurance_rows,
    build_statistics_csv_rows,
)


def _pen(**kw):
    base = dict(id=1, brand="Pelikan", model="M800", color=None, is_active=True,
                purchase_price=None, purchase_currency="CHF", purchase_date=None,
                current_market_value=None, market_currency=None,
                insurance_value=None, insurance_currency=None, tags=None)
    base.update(kw)
    return NS(**base)


def test_value_summary_totals_and_delta():
    pens = [
        _pen(id=1, purchase_price=100.0, current_market_value=150.0, insurance_value=160.0),
        _pen(id=2, purchase_price=200.0),  # kein Marktwert → zählt nicht ins Delta
        _pen(id=3, purchase_price=50.0, current_market_value=40.0),
    ]
    s = collection_value_summary(pens)
    assert s["counted"] == 3 and s["valued"] == 2
    assert s["purchase_total"] == 350.0
    assert s["market_total"] == 190.0
    assert s["insurance_total"] == 160.0
    # Delta nur über gepaarte Werte: (150+40) - (100+50) = 40
    assert s["delta"] == 40.0
    assert abs(s["delta_pct"] - (40.0 / 150.0 * 100.0)) < 1e-9


def test_value_summary_ignores_inactive_and_handles_empty():
    pens = [_pen(is_active=False, purchase_price=999.0)]
    s = collection_value_summary(pens)
    assert s["counted"] == 0 and s["purchase_total"] == 0.0 and s["delta_pct"] is None


def test_value_summary_uses_convert_callable():
    pens = [_pen(purchase_price=100.0, purchase_currency="EUR")]
    s = collection_value_summary(pens, convert=lambda amount, cur: amount * 2)
    assert s["purchase_total"] == 200.0


def test_value_by_year_cumulative():
    pens = [
        _pen(id=1, purchase_date=date(2023, 5, 1), purchase_price=100.0),
        _pen(id=2, purchase_date=date(2023, 8, 1), purchase_price=50.0),
        _pen(id=3, purchase_date=date(2025, 1, 1), purchase_price=200.0),
        _pen(id=4, purchase_date=None, purchase_price=999.0),  # ohne Datum ignoriert
    ]
    rows = value_by_year(pens)
    assert [r["year"] for r in rows] == [2023, 2025]
    assert rows[0]["count"] == 2 and rows[0]["purchase_total"] == 150.0
    assert rows[0]["cumulative_total"] == 150.0
    assert rows[1]["cumulative_total"] == 350.0


def test_budget_status_levels():
    assert budget_status(50, 0)["level"] == "none"
    assert budget_status(50, 100)["level"] == "ok"
    assert budget_status(80, 100)["level"] == "warn"
    assert budget_status(100, 100)["level"] == "warn"
    over = budget_status(150, 100)
    assert over["level"] == "over" and over["remaining"] == -50


def test_stale_ranking_orders_never_first_then_oldest():
    pens = [NS(id=1, brand="A", model="Eins", is_active=True, is_archived=False),
            NS(id=2, brand="B", model="Zwei", is_active=True, is_archived=False),
            NS(id=3, brand="C", model="Drei", is_active=True, is_archived=False)]
    loads = [NS(pen_id=1, ink_id=None, loaded_date=date(2026, 6, 1), cleaned_date=None),
             NS(pen_id=2, ink_id=None, loaded_date=date(2026, 1, 1), cleaned_date=date(2026, 2, 1))]
    rows = stale_ranking(pens, loads, kind="pen", reference=date(2026, 6, 10))
    assert rows[0]["id"] == 3 and rows[0]["never"] is True
    assert rows[1]["id"] == 2 and rows[1]["days"] == (date(2026, 6, 10) - date(2026, 2, 1)).days
    assert rows[2]["id"] == 1 and rows[2]["days"] == 9


def test_stale_ranking_skips_inactive_and_respects_limit():
    pens = [NS(id=1, brand="A", model="X", is_active=False, is_archived=False),
            NS(id=2, brand="B", model="Y", is_active=True, is_archived=False),
            NS(id=3, brand="C", model="Z", is_active=True, is_archived=False)]
    rows = stale_ranking(pens, [], kind="pen", limit=1)
    assert len(rows) == 1 and rows[0]["id"] in (2, 3)


def test_insurance_rows_header_and_values():
    pens = [_pen(purchase_price=100.0, current_market_value=120.5,
                 insurance_value=130.0, purchase_date=date(2024, 3, 2), tags="Grail"),
            _pen(is_active=False)]
    rows = build_insurance_rows(pens)
    assert rows[0][0] == "Marke" and len(rows) == 2  # Inaktive nicht exportiert
    assert rows[1][3] == "2024-03-02" and rows[1][4] == "100.00" and rows[1][6] == "120.50"


def test_statistics_csv_rows_structure():
    stats = {"total_default": 300.0, "count": 2,
             "by_type": {"pen": {"item_type": "pen", "total_default": 300.0}}}
    rows = build_statistics_csv_rows(stats, [{"label": "P1", "days": 5}], [], {"purchase_total": 300.0, "market_total": 0, "insurance_total": 0, "delta": 0})
    assert rows[0] == ["Sektion", "Feld", "Wert"]
    sections = {r[0] for r in rows[1:]}
    assert {"Ausgaben", "Ausgaben je Kategorie", "Meistgenutzte Füller", "Sammlungswert"} <= sections
