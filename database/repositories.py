"""Repository-Schicht (Enterprise-Audit v0.3.00, P1 Architektur).

Bündelt die bislang in Widgets verstreuten ``session.query(...)``-Aufrufe.
Die Repositories sind bewusst dünn: Sie kapseln nur Abfragen, keine
Geschäftslogik, und arbeiten auf einer übergebenen Session (kein eigenes
Öffnen/Schließen – der Lebenszyklus bleibt beim Aufrufer bzw. Service).

Damit werden Datenzugriffe testbar (Fake-Session genügt) und die
Audit-Kennzahl „UI-Dateien mit direktem Sessionzugriff" sinkt schrittweise;
das Ratchet-Gate ``tools/db_access_audit.py`` verhindert Rückschritte.
"""
from __future__ import annotations

from typing import Any, List, Optional

from database.models import (Expense, Ink, InkLoad, Nib, NibFormat, Paper,
                             Pen, PenNibSetup, WritingSample)


class _BaseRepository:
    def __init__(self, session: Any):
        self.session = session


class PenRepository(_BaseRepository):
    def count(self) -> int:
        return self.session.query(Pen).count()

    def all(self) -> List[Pen]:
        return self.session.query(Pen).all()

    def all_sorted(self) -> List[Pen]:
        return self.session.query(Pen).order_by(Pen.brand, Pen.model).all()

    def active(self) -> List[Pen]:
        return self.session.query(Pen).filter_by(is_active=True).all()

    def active_sorted(self) -> List[Pen]:
        return (
            self.session.query(Pen)
            .filter_by(is_active=True)
            .order_by(Pen.brand, Pen.model)
            .all()
        )

    def find_variant(
        self,
        brand: str,
        model: str,
        color: Optional[str],
        capacity_ml: Optional[float],
        *,
        only_active: bool = False,
    ) -> Optional[Pen]:
        """Exakte Modellvariante (CSV-Import-Match bzw. Dublettenprüfung)."""
        q = self.session.query(Pen).filter(
            Pen.brand == brand,
            Pen.model == model,
            Pen.color == color,
            Pen.ink_capacity_ml == capacity_ml,
        )
        if only_active:
            q = q.filter(Pen.is_active == True)  # noqa: E712 - SQLA-Ausdruck
        return q.first()

    def get(self, pen_id: int) -> Optional[Pen]:
        return self.session.get(Pen, pen_id)


class InkRepository(_BaseRepository):
    def count(self) -> int:
        return self.session.query(Ink).count()

    def all_sorted(self) -> List[Ink]:
        return self.session.query(Ink).order_by(Ink.brand, Ink.name).all()

    def usable_sorted(self) -> List[Ink]:
        """Befüllbare Tinten: weder leer noch archiviert, sortiert."""
        return (
            self.session.query(Ink)
            .filter_by(is_empty=False, is_archived=False)
            .order_by(Ink.brand, Ink.name)
            .all()
        )

    def find_variant(
        self,
        brand: str,
        name: str,
        bottle_size_ml: Optional[float],
        *,
        only_usable: bool = False,
    ) -> Optional[Ink]:
        """Exakte Flaschenvariante (Import-Match bzw. Dublettenprüfung)."""
        q = self.session.query(Ink).filter(
            Ink.brand == brand,
            Ink.name == name,
            Ink.bottle_size_ml == bottle_size_ml,
        )
        if only_usable:
            q = q.filter(Ink.is_archived == False, Ink.is_empty == False)  # noqa: E712
        return q.first()

    def active(self) -> List[Ink]:
        return self.session.query(Ink).filter_by(is_archived=False).all()

    def archived_count(self) -> int:
        return self.session.query(Ink).filter_by(is_archived=True).count()

    def get(self, ink_id: int) -> Optional[Ink]:
        return self.session.get(Ink, ink_id)


class PaperRepository(_BaseRepository):
    def all(self) -> List[Paper]:
        return self.session.query(Paper).all()


class ExpenseRepository(_BaseRepository):
    def all(self) -> List[Expense]:
        return self.session.query(Expense).all()

    def for_pen(self, pen_id: int) -> List[Expense]:
        """Buchungshistorie eines Füllers, neueste zuerst (NULL-Daten zuletzt)."""
        return (
            self.session.query(Expense)
            .filter(Expense.pen_id == pen_id)
            .order_by(Expense.purchase_date.desc().nullslast(), Expense.id.desc())
            .all()
        )

    def find_auto_purchase_for_pen(self, pen_id: int, auto_tag: str) -> Optional[Expense]:
        return (
            self.session.query(Expense)
            .filter(
                Expense.pen_id == pen_id,
                Expense.notes == auto_tag,
                Expense.item_type == "pen",
            )
            .first()
        )


class InkLoadRepository(_BaseRepository):
    def recent(self, limit: int = 8) -> List[InkLoad]:
        return (
            self.session.query(InkLoad)
            .order_by(InkLoad.loaded_date.desc())
            .limit(limit)
            .all()
        )


class NibRepository(_BaseRepository):
    def all_sorted(self) -> List[Nib]:
        return (
            self.session.query(Nib)
            .order_by(Nib.manufacturer, Nib.size, Nib.grind)
            .all()
        )

    def by_format(self, format_id: Optional[int]) -> List[Nib]:
        if not format_id:
            return []
        return self.session.query(Nib).filter(Nib.format_id == format_id).all()


class NibFormatRepository(_BaseRepository):
    def all(self) -> List[NibFormat]:
        return self.session.query(NibFormat).all()


class PenNibSetupRepository(_BaseRepository):
    def for_pen(self, pen_id: int) -> List[PenNibSetup]:
        return (
            self.session.query(PenNibSetup)
            .filter(PenNibSetup.pen_id == pen_id)
            .order_by(PenNibSetup.installed_date.desc())
            .all()
        )


class WritingSampleRepository(_BaseRepository):
    def for_pen(self, pen_id: int) -> List[WritingSample]:
        return (
            self.session.query(WritingSample)
            .filter(WritingSample.pen_id == pen_id)
            .order_by(WritingSample.written_at.desc(), WritingSample.id.desc())
            .all()
        )
