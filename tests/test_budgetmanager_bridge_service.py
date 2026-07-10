import json

from logic.budget_export_service import (
    expense_to_budgetmanager_record,
    load_budgetmanager_expense_proposals,
)


class DummyExpense:
    id = 5
    item_type = "paper"
    currency = "CHF"
    total = 9.5
    purchase_date = "2026-07-04"
    description = "Midori MD"
    vendor = ""
    notes = ""
    amount = 9.5
    shipping = 0
    customs = 0
    pen_id = None
    ink_id = None
    nib_id = None
    paper_id = None


def test_fpm_expense_to_budgetmanager_record_is_reviewable_import():
    rec = expense_to_budgetmanager_record(DummyExpense())
    assert rec["schema"] == "budgetmanager.import.v1"
    assert rec["external_id"] == "fpm:expense:5"
    assert rec["category_path"] == "Hobby/Papier"


def test_budgetmanager_to_fpm_jsonl_proposal_guess_item_type(tmp_path):
    path = tmp_path / "budgetmanager_to_fpm.jsonl"
    path.write_text(
        json.dumps({"schema": "fpm.import.manifest.v1"})
        + "\n"
        + json.dumps(
            {
                "schema": "fpm.import.v1",
                "external_id": "budgetmanager:tracking:77",
                "date": "2026-07-04",
                "amount": 42,
                "currency": "CHF",
                "category": "Füller",
                "description": "Pilot Custom",
                "source": "BudgetManager",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    proposals = load_budgetmanager_expense_proposals(path)
    assert proposals[0].external_id == "budgetmanager:tracking:77"
    assert proposals[0].item_type == "pen"


def test_load_budgetmanager_savings_goal_mirror(tmp_path):
    from logic.budget_export_service import load_budgetmanager_savings_goals

    path = tmp_path / "budgetmanager_savings_goals.jsonl"
    path.write_text(
        json.dumps({"schema": "fpm.savings_goals.manifest.v1"})
        + "\n"
        + json.dumps(
            {
                "schema": "fpm.savings_goal.v1",
                "external_id": "budgetmanager:savings_goal:1",
                "source": "BudgetManager",
                "item_type": "pen",
                "label": "Pilot Custom 823",
                "goal_name": "Füller-Sparziel",
                "status": "sparend",
                "target_amount": 300,
                "current_amount": 120,
                "remaining_amount": 180,
                "progress_percent": 40,
                "currency": "CHF",
                "deadline": "2026-09-01",
                "category": "Füller",
                "visible": True,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    goals = load_budgetmanager_savings_goals(path)
    assert len(goals) == 1
    assert goals[0].external_id == "budgetmanager:savings_goal:1"
    assert goals[0].item_type == "pen"
    assert goals[0].label == "Pilot Custom 823"
    assert goals[0].remaining_amount == 180
    assert goals[0].progress_percent == 40.0
