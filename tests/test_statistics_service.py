from datetime import date, datetime
from types import SimpleNamespace

from logic.statistics_service import period_bounds, summarize_expenses, rank_usage
from i18n.translator import LocaleService


def test_period_bounds_week_month_year():
    assert period_bounds("week", date(2026, 6, 4)) == (date(2026, 6, 1), date(2026, 6, 8))
    assert period_bounds("month", date(2026, 6, 4)) == (date(2026, 6, 1), date(2026, 7, 1))
    assert period_bounds("year", date(2026, 6, 4)) == (date(2026, 1, 1), date(2027, 1, 1))
    assert period_bounds("overall", date(2026, 6, 4)) == (None, None)


def test_summarize_expenses_filters_period_and_type():
    expenses = [
        SimpleNamespace(item_type="pen", purchase_date=datetime(2026, 6, 2), total=100.0, currency="CHF"),
        SimpleNamespace(item_type="ink", purchase_date=datetime(2026, 6, 3), total=20.0, currency="EUR"),
        SimpleNamespace(item_type="service", purchase_date=datetime(2026, 5, 30), total=50.0, currency="CHF"),
    ]
    stats = summarize_expenses(
        expenses,
        period="month",
        reference=date(2026, 6, 4),
        item_types={"pen", "ink"},
        convert_to_default=lambda amount, currency: amount * (2 if currency == "EUR" else 1),
    )
    assert stats["count"] == 2
    assert stats["total_default"] == 140.0
    assert stats["by_type"]["pen"]["count"] == 1
    assert stats["by_type"]["ink"]["total_default"] == 40.0


def test_rank_usage_counts_overlap_days_and_fills():
    pen_a = SimpleNamespace(id=1, brand="Pilot", model="Custom")
    pen_b = SimpleNamespace(id=2, brand="Lamy", model="2000")
    ink = SimpleNamespace(id=9, brand="Pilot", name="Tsuki-yo")
    loads = [
        SimpleNamespace(pen=pen_a, pen_id=1, ink=ink, ink_id=9, loaded_date=datetime(2026, 5, 30), cleaned_date=datetime(2026, 6, 3), volume_ml=1.0),
        SimpleNamespace(pen=pen_b, pen_id=2, ink=ink, ink_id=9, loaded_date=datetime(2026, 6, 4), cleaned_date=None, volume_ml=1.2),
    ]
    rows = rank_usage(loads, kind="pen", period="week", reference=date(2026, 6, 4), today=date(2026, 6, 5))
    assert rows[0]["label"] == "Pilot Custom"
    assert rows[0]["usage_days"] == 3
    assert rows[0]["fill_count"] == 0  # Befüllung war vor der Woche, Nutzung zählt trotzdem.
    assert rows[1]["fill_count"] == 1


def test_rank_usage_for_ink_aggregates_multiple_pens():
    pen_a = SimpleNamespace(id=1, brand="Pilot", model="Custom")
    pen_b = SimpleNamespace(id=2, brand="Lamy", model="2000")
    ink = SimpleNamespace(id=9, brand="Pilot", name="Tsuki-yo")
    loads = [
        SimpleNamespace(pen=pen_a, pen_id=1, ink=ink, ink_id=9, loaded_date=datetime(2026, 6, 1), cleaned_date=datetime(2026, 6, 2), volume_ml=1.0),
        SimpleNamespace(pen=pen_b, pen_id=2, ink=ink, ink_id=9, loaded_date=datetime(2026, 6, 4), cleaned_date=datetime(2026, 6, 4), volume_ml=0.8),
    ]
    rows = rank_usage(loads, kind="ink", period="month", reference=date(2026, 6, 4), today=date(2026, 6, 5))
    assert len(rows) == 1
    assert rows[0]["label"] == "Pilot Tsuki-yo"
    assert rows[0]["usage_days"] == 3
    assert rows[0]["fill_count"] == 2
    assert rows[0]["volume_ml"] == 1.8


def test_locale_service_formats_dates_by_setting():
    locale = LocaleService.__new__(LocaleService)
    locale._date_format = "MM/DD/YYYY"
    assert locale.format_date(date(2026, 6, 4)) == "06/04/2026"
    assert locale.format_date(datetime(2026, 12, 31, 15, 10)) == "12/31/2026"

    locale._date_format = "YYYY-MM-DD"
    assert locale.format_date(date(2026, 6, 4)) == "2026-06-04"
    assert locale.qt_date_format == "yyyy-MM-dd"


def test_summarize_expenses_keeps_all_release_categories_when_not_filtered():
    expenses = [
        SimpleNamespace(item_type="nib", purchase_date=datetime(2026, 6, 2), total=30.0, currency="CHF"),
        SimpleNamespace(item_type="paper", purchase_date=datetime(2026, 6, 3), total=15.0, currency="CHF"),
        SimpleNamespace(item_type="shipping", purchase_date=datetime(2026, 6, 4), total=7.5, currency="CHF"),
    ]
    stats = summarize_expenses(
        expenses,
        period="month",
        reference=date(2026, 6, 4),
        item_types=None,
        convert_to_default=lambda amount, currency: amount,
    )
    assert stats["count"] == 3
    assert set(stats["by_type"]) == {"nib", "paper", "shipping"}


def test_summarize_expenses_exposes_average_default():
    expenses = [
        SimpleNamespace(item_type="pen", purchase_date=datetime(2026, 6, 2), total=100.0, currency="CHF"),
        SimpleNamespace(item_type="ink", purchase_date=datetime(2026, 6, 3), total=50.0, currency="CHF"),
    ]
    stats = summarize_expenses(
        expenses,
        period="month",
        reference=date(2026, 6, 4),
        convert_to_default=lambda amount, currency: amount,
    )
    assert stats["count"] == 2
    assert stats["total_default"] == 150.0
    assert stats["average_default"] == 75.0

    empty_stats = summarize_expenses([], period="overall")
    assert empty_stats["average_default"] == 0.0
