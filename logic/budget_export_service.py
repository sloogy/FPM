"""FPM ↔ BudgetManager bridge service.

The bridge is deliberately file based (JSONL) and reviewable.  The FPM database
is the source of truth for collection details; BudgetManager is the source of
truth for budgets and bookings.  No tool writes directly into the other tool's
SQLite database.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable


DEFAULT_CATEGORY_MAP = {
    "pen": "Hobby/Füller",
    "ink": "Hobby/Tinte",
    "nib": "Hobby/Federn",
    "paper": "Hobby/Papier",
    "accessory": "Hobby/Zubehör",
    "service": "Hobby/Service",
    "shipping": "Hobby/Versand/Zoll",
    "customs": "Hobby/Versand/Zoll",
    "other": "Hobby/Sonstiges",
}

BRIDGE_DIR_NAME = "fpm_budgetmanager_bridge"
FPM_TO_BUDGETMANAGER_FILE = "fpm_to_budgetmanager.jsonl"
BUDGETMANAGER_TO_FPM_FILE = "budgetmanager_to_fpm.jsonl"
BUDGETMANAGER_SAVINGS_GOALS_FILE = "budgetmanager_savings_goals.jsonl"
FPM_IMPORT_MARKER = "#bridge_id="


@dataclass(frozen=True)
class BudgetExportResult:
    path: Path
    count: int
    total: float
    currencies: tuple[str, ...]


@dataclass(frozen=True)
class FpmImportProposal:
    external_id: str
    source: str
    item_type: str
    purchase_date: date
    amount: float
    currency: str
    description: str
    vendor: str
    notes: str
    duplicate: bool = False


@dataclass(frozen=True)
class BudgetManagerSavingsGoal:
    external_id: str
    source: str
    item_type: str
    label: str
    goal_name: str
    status: str
    target_amount: float
    current_amount: float
    remaining_amount: float
    progress_percent: float
    currency: str
    deadline: str
    category: str
    notes: str


def default_bridge_dir() -> Path:
    return Path.home() / BRIDGE_DIR_NAME


def default_fpm_to_budgetmanager_path() -> Path:
    return default_bridge_dir() / FPM_TO_BUDGETMANAGER_FILE


def default_budgetmanager_to_fpm_path() -> Path:
    return default_bridge_dir() / BUDGETMANAGER_TO_FPM_FILE


def default_budgetmanager_savings_goals_path() -> Path:
    return default_bridge_dir() / BUDGETMANAGER_SAVINGS_GOALS_FILE


def _iso_date(value: Any) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if value:
        try:
            return datetime.fromisoformat(str(value)).date().isoformat()
        except Exception:
            pass
    return date.today().isoformat()


def _parse_date(value: Any) -> date:
    try:
        return date.fromisoformat(_iso_date(value))
    except Exception:
        return date.today()


def _label(exp: Any) -> str:
    linked = getattr(exp, "linked_label", None)
    if linked:
        return str(linked)
    desc = getattr(exp, "description", None)
    if desc:
        return str(desc)
    return str(getattr(exp, "item_type", None) or "FPM-Ausgabe")


def expense_to_budgetmanager_record(exp: Any, *, source: str = "FPM") -> dict[str, Any]:
    """Konvertiert eine Ausgabe in einen stabilen BudgetManager-Vorschlag."""
    item_type = (getattr(exp, "item_type", None) or "other").lower()
    currency = getattr(exp, "currency", None) or "CHF"
    total = float(getattr(exp, "total", 0.0) or 0.0)
    exp_id = getattr(exp, "id", None)
    if exp_id is not None:
        external_id = f"{source.lower()}:expense:{exp_id}"
    else:
        external_id = (
            f"{source.lower()}:expense:"
            f"{_iso_date(getattr(exp, 'purchase_date', None))}:{_label(exp)}"
        )
    return {
        "schema": "budgetmanager.import.v1",
        "operation": "upsert",
        "external_id": external_id,
        "source": source,
        "date": _iso_date(getattr(exp, "purchase_date", None)),
        "amount": round(total, 2),
        "currency": currency,
        "category_path": DEFAULT_CATEGORY_MAP.get(item_type, DEFAULT_CATEGORY_MAP["other"]),
        "description": _label(exp),
        "counterparty": getattr(exp, "vendor", None) or "",
        "notes": getattr(exp, "notes", None) or "",
        "metadata": {
            "item_type": item_type,
            "amount": float(getattr(exp, "amount", 0.0) or 0.0),
            "shipping": float(getattr(exp, "shipping", 0.0) or 0.0),
            "customs": float(getattr(exp, "customs", 0.0) or 0.0),
            "order_number": getattr(exp, "order_number", None) or "",
            "payment_method": getattr(exp, "payment_method", None) or "",
            "pen_id": getattr(exp, "pen_id", None),
            "ink_id": getattr(exp, "ink_id", None),
            "nib_id": getattr(exp, "nib_id", None),
            "paper_id": getattr(exp, "paper_id", None),
        },
    }


def export_expenses_jsonl(
    expenses: Iterable[Any], path: str | Path, *, source: str = "FPM"
) -> BudgetExportResult:
    """Schreibt BudgetManager-Importzeilen und liefert eine kurze Summary."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    total = 0.0
    currencies: set[str] = set()
    with out.open("w", encoding="utf-8", newline="\n") as fh:
        header = {
            "schema": "budgetmanager.import.manifest.v1",
            "source": source,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "mode": "reviewable_bridge_import",
        }
        fh.write(json.dumps(header, ensure_ascii=False, sort_keys=True) + "\n")
        for exp in expenses:
            record = expense_to_budgetmanager_record(exp, source=source)
            fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
            total += float(record["amount"] or 0.0)
            currencies.add(str(record["currency"] or "CHF"))
    return BudgetExportResult(
        path=out,
        count=count,
        total=round(total, 2),
        currencies=tuple(sorted(currencies)),
    )


def sync_default_outbox(expenses: Iterable[Any]) -> BudgetExportResult:
    """Aktualisiert die automatische FPM→BudgetManager-Bridge-Datei."""
    return export_expenses_jsonl(expenses, default_fpm_to_budgetmanager_path())


def sync_default_outbox_from_session(session: Any) -> BudgetExportResult:
    """Liest alle FPM-Ausgaben aus einer SQLAlchemy-Session und schreibt die Outbox."""
    from database.models import Expense

    expenses = (
        session.query(Expense)
        .order_by(Expense.purchase_date.asc().nullslast(), Expense.id.asc())
        .all()
    )
    return sync_default_outbox(expenses)


def sync_default_outbox_safely() -> None:
    """Best-effort Outbox-Sync nach UI-Commits; Fehler dürfen die App nicht blockieren."""
    try:
        from database.db import get_session

        session = get_session()
        try:
            sync_default_outbox_from_session(session)
        finally:
            session.close()
    except Exception:
        # Bridge darf niemals die eigentliche Sammlung beschädigen oder blockieren.
        pass


def _iter_jsonl_records(path: str | Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    p = Path(path)
    if not p.exists():
        return records
    with p.open("r", encoding="utf-8") as fh:
        for line_no, raw in enumerate(fh, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Ungültige JSONL-Zeile {line_no}: {exc}") from exc
            if isinstance(rec, dict):
                records.append(rec)
    return records


def _normalize_item_type(value: Any, description: str = "", category: str = "") -> str:
    raw = f"{value or ''} {description or ''} {category or ''}".lower()
    checks = [
        ("pen", ("füller", "fueller", "fountain pen", " fountain", "pen", "pilot", "asvine", "gravitas", "majohn")),
        ("ink", ("tinte", "ink", "iroshizuku", "diamine", "edelstein")),
        ("nib", ("feder", "nib", "stub", "ef", "extra fine")),
        ("paper", ("papier", "paper", "notiz", "journal", "tomoe", "midori", "rhodia")),
        ("service", ("service", "reparatur", "repair", "clean", "reinigung")),
        ("accessory", ("zubehör", "zubehoer", "accessory", "case", "etui")),
    ]
    for item_type, keywords in checks:
        if any(k in raw for k in keywords):
            return item_type
    raw_type = str(value or "").strip().lower()
    return raw_type if raw_type in set(DEFAULT_CATEGORY_MAP) else "other"


def load_budgetmanager_expense_proposals(
    path: str | Path, *, existing_external_ids: set[str] | None = None
) -> list[FpmImportProposal]:
    """Lädt BudgetManager→FPM-Vorschläge aus JSONL, ohne etwas zu speichern."""
    existing = existing_external_ids or set()
    proposals: list[FpmImportProposal] = []
    for rec in _iter_jsonl_records(path):
        if rec.get("schema") not in {"fpm.import.v1", "fpm.expense.v1"}:
            continue
        external_id = str(rec.get("external_id") or "").strip()
        if not external_id:
            continue
        description = str(rec.get("description") or rec.get("details") or "BudgetManager-Ausgabe").strip()
        category = str(rec.get("category") or rec.get("category_path") or "").strip()
        item_type = _normalize_item_type(rec.get("item_type"), description, category)
        amount = float(rec.get("amount") or 0.0)
        if amount <= 0:
            continue
        proposals.append(
            FpmImportProposal(
                external_id=external_id,
                source=str(rec.get("source") or "BudgetManager"),
                item_type=item_type,
                purchase_date=_parse_date(rec.get("date")),
                amount=round(amount, 2),
                currency=str(rec.get("currency") or "CHF"),
                description=description,
                vendor=str(rec.get("counterparty") or rec.get("vendor") or ""),
                notes=str(rec.get("notes") or ""),
                duplicate=external_id in existing,
            )
        )
    return proposals


def existing_fpm_bridge_ids(session: Any) -> set[str]:
    """Findet bereits importierte BudgetManager-Bridge-IDs in Expense.notes."""
    from database.models import Expense

    ids: set[str] = set()
    rows = session.query(Expense.notes).filter(Expense.notes.like(f"%{FPM_IMPORT_MARKER}%")).all()
    for row in rows:
        note = str(row[0] or "")
        for part in note.split():
            if part.startswith(FPM_IMPORT_MARKER):
                ids.add(part[len(FPM_IMPORT_MARKER) :].strip())
    return ids


def import_budgetmanager_proposals(session: Any, proposals: Iterable[FpmImportProposal]) -> int:
    """Übernimmt nicht-duplizierte BudgetManager-Vorschläge als FPM-Ausgaben."""
    from database.models import Expense

    count = 0
    for p in proposals:
        if p.duplicate:
            continue
        marker = f"{FPM_IMPORT_MARKER}{p.external_id}"
        notes = "\n".join(x for x in [p.notes, f"Import aus {p.source}; {marker}"] if x)
        session.add(
            Expense(
                item_type=p.item_type,
                amount=float(p.amount),
                shipping=0.0,
                customs=0.0,
                currency=p.currency or "CHF",
                purchase_date=datetime.combine(p.purchase_date, datetime.min.time()),
                description=p.description,
                vendor=p.vendor or None,
                notes=notes,
            )
        )
        count += 1
    return count


def load_budgetmanager_savings_goals(
    path: str | Path | None = None, *, visible_only: bool = True
) -> list[BudgetManagerSavingsGoal]:
    """Lädt die read-only Sparziel-Spiegelung aus BudgetManager.

    FPM speichert diese Daten nicht dauerhaft; sie dienen nur zur Anzeige auf
    dem Dashboard bzw. bei verknüpften Wunsch-/Füller-Projekten.
    """
    src = Path(path) if path else default_budgetmanager_savings_goals_path()
    goals: list[BudgetManagerSavingsGoal] = []
    for rec in _iter_jsonl_records(src):
        if rec.get("schema") != "fpm.savings_goal.v1":
            continue
        if visible_only and rec.get("visible") is False:
            continue
        external_id = str(rec.get("external_id") or "").strip()
        if not external_id:
            continue
        item_type = _normalize_item_type(
            rec.get("item_type"),
            str(rec.get("goal_name") or rec.get("label") or ""),
            str(rec.get("category") or ""),
        )
        target = float(rec.get("target_amount") or 0.0)
        current = float(rec.get("current_amount") or 0.0)
        remaining = float(rec.get("remaining_amount") if rec.get("remaining_amount") is not None else max(0.0, target - current))
        progress = float(rec.get("progress_percent") if rec.get("progress_percent") is not None else (0.0 if target <= 0 else current / target * 100.0))
        goals.append(
            BudgetManagerSavingsGoal(
                external_id=external_id,
                source=str(rec.get("source") or "BudgetManager"),
                item_type=item_type,
                label=str(rec.get("label") or rec.get("goal_name") or "Sparziel"),
                goal_name=str(rec.get("goal_name") or rec.get("label") or "Sparziel"),
                status=str(rec.get("status") or "sparend"),
                target_amount=round(target, 2),
                current_amount=round(current, 2),
                remaining_amount=round(max(0.0, remaining), 2),
                progress_percent=round(max(0.0, min(100.0, progress)), 1),
                currency=str(rec.get("currency") or "CHF"),
                deadline=str(rec.get("deadline") or ""),
                category=str(rec.get("category") or ""),
                notes=str(rec.get("notes") or ""),
            )
        )
    goals.sort(key=lambda g: (g.status != "sparend", g.deadline or "9999-12-31", g.label.lower()))
    return goals
