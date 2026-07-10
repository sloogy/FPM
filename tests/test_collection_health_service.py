from datetime import date, datetime
from types import SimpleNamespace
import json

from logic.collection_health_service import build_collection_health
from logic.budget_export_service import expense_to_budgetmanager_record, export_expenses_jsonl


def test_collection_health_prioritizes_overdue_loads():
    ink = SimpleNamespace(id=7, brand="Diamine", name="Shimmer", has_shimmer=True, is_pigment=False, cleaning_effort=5, max_days_in_pen=10)
    load = SimpleNamespace(ink=ink, ink_id=7, loaded_date=datetime(2026, 6, 1), cleaned_date=None)
    pen = SimpleNamespace(id=1, brand="Pilot", model="Custom", is_active=True, availability_status="available", rotation_blocked=False, current_ink_load=load)

    rows = build_collection_health(pens=[pen], inks=[ink], today=date(2026, 6, 20), limit=5)

    assert rows[0].code == "load_overdue"
    assert rows[0].severity == "critical"
    assert any(r.code == "high_cleaning_active" for r in rows)


def test_collection_health_finds_empty_pen_low_ink_paper_and_warranty():
    pen = SimpleNamespace(id=1, brand="Lamy", model="2000", is_active=True, availability_status="available", rotation_blocked=False, current_ink_load=None, rotation_role="work", purchase_price=150.0, image_path=None)
    ink = SimpleNamespace(id=2, brand="Pilot", name="Tsuki-yo", remaining_ml=5.0, bottle_size_ml=50.0, is_empty=False, is_archived=False)
    paper = SimpleNamespace(brand="Midori", name="MD", pages_used=190, pages_total=200)
    exp = SimpleNamespace(description="Nib service", warranty_until=date(2026, 7, 10), linked_label="Gravitas EF")

    rows = build_collection_health(pens=[pen], inks=[ink], papers=[paper], expenses=[exp], today=date(2026, 7, 1), limit=10)
    codes = {r.code for r in rows}

    assert {"empty_pen", "ink_low", "paper_low", "warranty_expiring", "missing_pen_photo"} <= codes


def test_budget_export_record_is_budgetmanager_import_v1():
    exp = SimpleNamespace(
        id=42, item_type="ink", purchase_date=date(2026, 6, 4), total=31.5,
        amount=24.0, shipping=5.0, customs=2.5, currency="CHF", linked_label="Pilot Tsuki-yo",
        vendor="Stilo", notes="", order_number="A-1", payment_method="card",
        pen_id=None, ink_id=9, nib_id=None, paper_id=None,
    )
    rec = expense_to_budgetmanager_record(exp)
    assert rec["schema"] == "budgetmanager.import.v1"
    assert rec["operation"] == "upsert"
    assert rec["external_id"] == "fpm:expense:42"
    assert rec["category_path"] == "Hobby/Tinte"
    assert rec["amount"] == 31.5
    assert rec["metadata"]["shipping"] == 5.0


def test_budget_export_jsonl_writes_manifest_and_records(tmp_path):
    exp = SimpleNamespace(
        id=1, item_type="paper", purchase_date=date(2026, 6, 5), total=12.0,
        amount=12.0, shipping=0.0, customs=0.0, currency="CHF", linked_label="Midori MD",
        vendor="Shop", notes="", order_number="", payment_method="", pen_id=None, ink_id=None, nib_id=None, paper_id=3,
    )
    out = tmp_path / "fpm_export.jsonl"
    result = export_expenses_jsonl([exp], out)
    lines = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert result.count == 1
    assert result.total == 12.0
    assert lines[0]["schema"] == "budgetmanager.import.manifest.v1"
    assert lines[1]["category_path"] == "Hobby/Papier"
