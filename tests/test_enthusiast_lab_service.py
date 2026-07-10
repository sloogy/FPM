from datetime import datetime, timedelta
from types import SimpleNamespace as NS

from logic.enthusiast_lab_service import (
    ink_stock_rows,
    color_gap_rows,
    nib_history_rows,
    cleaning_stats_rows,
)


def ink(**kw):
    base = dict(id=1, brand="Diamine", name="Sepia", bottle_size_ml=30.0, remaining_ml=20.0,
                reorder_threshold_ml=None, is_empty=False, is_archived=False, color_family="brown",
                color_type="warm sepia", notes="", character_notes="")
    base.update(kw)
    return NS(**base)


def test_ink_stock_rows_recommends_reorder_and_handles_unknown():
    rows = ink_stock_rows([
        ink(id=1, remaining_ml=2.0, reorder_threshold_ml=5.0),
        ink(id=2, name="Unknown", bottle_size_ml=50.0, remaining_ml=None),
        ink(id=3, name="Full", remaining_ml=29.0),
    ])
    by_id = {r.ink_id: r for r in rows}
    assert by_id[1].status == "reorder" and by_id[1].fill_pct < 10
    assert by_id[2].status == "unknown"
    assert by_id[3].status == "ok"


def test_color_gap_rows_detects_warm_brown_subtone_gap():
    rows = color_gap_rows([
        ink(id=1, name="Chocolate", color_family="brown", color_type="dark neutral brown"),
        ink(id=2, name="Royal Blue", color_family="blue", color_type="business blue"),
    ])
    statuses = {(r.family, r.status) for r in rows}
    assert ("warm_brown", "missing_subtone") in statuses
    assert any(r.family == "green" and r.status == "missing" for r in rows)


def test_nib_history_rows_orders_and_calculates_days():
    pen = NS(id=1, brand="Asvine", model="V800")
    nib = NS(id=7, display_label="Jowo #6 EF")
    setup = NS(pen_id=1, nib_id=7, pen=pen, nib=nib, installed_date=datetime(2026, 7, 1),
               removed_date=None, is_active=True, setup_label="EF Alltag", install_reason="Test",
               removal_reason=None, compatibility_notes="", feel_notes="gut")
    rows = nib_history_rows([pen], [setup], reference=datetime(2026, 7, 4))
    assert rows[0].pen_label == "Asvine V800"
    assert rows[0].nib_label == "Jowo #6 EF"
    assert rows[0].active is True
    assert rows[0].days_installed == 3


def test_cleaning_stats_rows_marks_hard_inks():
    ink_obj = ink(id=1, brand="Diamine", name="Skull & Roses")
    logs = [
        NS(ink_id=1, duration_minutes=25, difficulty_level=5, flush_cycles=8, cleaned_at=datetime.now() - timedelta(days=2)),
        NS(ink_id=1, duration_minutes=20, difficulty_level=4, flush_cycles=6, cleaned_at=datetime.now()),
    ]
    rows = cleaning_stats_rows(logs, [ink_obj])
    assert rows[0].ink_label == "Diamine Skull & Roses"
    assert rows[0].cleanings == 2
    assert rows[0].status == "hard"
    assert rows[0].avg_minutes == 22.5
