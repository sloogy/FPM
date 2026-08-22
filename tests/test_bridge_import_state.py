from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from logic.bridge_import_state import (
    imported_ids,
    migrate_legacy_ids,
    remember_import,
)


def _session():
    engine = create_engine("sqlite:///:memory:")
    return Session(engine)


def test_importstatus_ist_unabhaengig_von_expense_notizen():
    session = _session()
    remember_import(
        session,
        "budgetmanager:tracking:77",
        payload_hash="abc123",
        local_object_id=12,
    )
    session.commit()
    assert imported_ids(session) == {"budgetmanager:tracking:77"}


def test_legacy_marker_wird_in_status_tabelle_migriert():
    session = _session()
    found = migrate_legacy_ids(
        session,
        [(5, "Import aus BudgetManager; #bridge_id=budgetmanager:tracking:5")],
        marker="#bridge_id=",
    )
    session.commit()
    assert found == {"budgetmanager:tracking:5"}
    assert imported_ids(session) == {"budgetmanager:tracking:5"}
