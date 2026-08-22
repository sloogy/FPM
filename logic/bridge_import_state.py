"""Persistenter Importstatus für externe LifePlanner-/BudgetManager-Datensätze.

Technische Identität darf nicht von frei editierbaren Expense-Notizen abhängen.
Die Tabelle liegt in derselben FPM-SQLite-Datenbank und wird lazy angelegt, so
dass bestehende Installationen keine separate Migration benötigen.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Iterable

from sqlalchemy import text

SOURCE_BUDGETMANAGER = "budgetmanager"


def ensure_table(session: Any) -> None:
    session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS bridge_import_state (
                source TEXT NOT NULL,
                external_id TEXT NOT NULL,
                payload_hash TEXT NOT NULL,
                status TEXT NOT NULL,
                local_object_type TEXT NOT NULL,
                local_object_id INTEGER,
                imported_at TEXT NOT NULL,
                PRIMARY KEY (source, external_id)
            )
            """
        )
    )


def proposal_hash(proposal: Any) -> str:
    payload = {
        "external_id": str(getattr(proposal, "external_id", "")),
        "source": str(getattr(proposal, "source", "")),
        "item_type": str(getattr(proposal, "item_type", "")),
        "purchase_date": str(getattr(proposal, "purchase_date", "")),
        "amount": round(float(getattr(proposal, "amount", 0.0) or 0.0), 2),
        "currency": str(getattr(proposal, "currency", "")),
        "description": str(getattr(proposal, "description", "")),
        "vendor": str(getattr(proposal, "vendor", "")),
        "notes": str(getattr(proposal, "notes", "")),
    }
    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def imported_ids(session: Any, *, source: str = SOURCE_BUDGETMANAGER) -> set[str]:
    ensure_table(session)
    rows = session.execute(
        text(
            "SELECT external_id FROM bridge_import_state "
            "WHERE source=:source AND status='imported'"
        ),
        {"source": source},
    )
    return {str(row[0]) for row in rows if row[0]}


def remember_import(
    session: Any,
    external_id: str,
    *,
    payload_hash: str,
    local_object_id: int | None,
    source: str = SOURCE_BUDGETMANAGER,
) -> None:
    ensure_table(session)
    session.execute(
        text(
            """
            INSERT INTO bridge_import_state
                (source, external_id, payload_hash, status, local_object_type,
                 local_object_id, imported_at)
            VALUES
                (:source, :external_id, :payload_hash, 'imported', 'expense',
                 :local_object_id, :imported_at)
            ON CONFLICT(source, external_id) DO UPDATE SET
                payload_hash=excluded.payload_hash,
                status='imported',
                local_object_type='expense',
                local_object_id=excluded.local_object_id,
                imported_at=excluded.imported_at
            """
        ),
        {
            "source": source,
            "external_id": external_id,
            "payload_hash": payload_hash,
            "local_object_id": local_object_id,
            "imported_at": datetime.now(timezone.utc).isoformat(),
        },
    )


def migrate_legacy_ids(
    session: Any,
    legacy_rows: Iterable[tuple[int | None, str]],
    *,
    marker: str,
) -> set[str]:
    """Übernimmt alte ``#bridge_id=``-Marker einmalig in die Status-Tabelle."""
    ensure_table(session)
    found: set[str] = set()
    for local_id, note in legacy_rows:
        for part in str(note or "").split():
            if not part.startswith(marker):
                continue
            external_id = part[len(marker) :].strip()
            if not external_id:
                continue
            found.add(external_id)
            remember_import(
                session,
                external_id,
                payload_hash="legacy-marker",
                local_object_id=int(local_id) if local_id is not None else None,
            )
    return found
