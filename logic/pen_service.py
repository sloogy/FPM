"""Pen-Service (v0.3.02): fachliche DB-Operationen der Füllerverwaltung.

Zieht die verbliebenen direkten Datenbankzugriffe aus ``ui/pen_widget.py``
und den Füller-Dialogen in Qt-freie, session-injizierbare Funktionen.
Dialog-Fragen (QMessageBox) bleiben im Widget; hier lebt nur Daten- und
Entscheidungslogik – damit verhaltenstestbar (``test_pen_ink_services_0302``).
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from database.models import Expense, NibFormat, Pen
from database.repositories import (
    ExpenseRepository,
    InkRepository,
    NibFormatRepository,
    NibRepository,
    PaperRepository,
    PenRepository,
    WritingSampleRepository,
)
from i18n.translator import LocaleService

AUTO_PURCHASE_TAG_PREFIX = "AUTO-PEN-PURCHASE:"


def normalize_text(value: Any) -> str:
    """Vergleichsnormalisierung für Feder-/Formatfelder (trim + lower)."""
    return (str(value).strip().lower()) if value not in (None, "") else ""


# ── Schreibproben-Vergleich ────────────────────────────────────────────────

def collect_sample_comparison_context(session: Any, pen_id: int) -> Tuple[list, dict, dict, dict]:
    """Alle Proben eines Füllers plus Lookup-Maps für den Vergleichsdialog."""
    samples = WritingSampleRepository(session).for_pen(pen_id)
    pens = {p.id: p for p in PenRepository(session).all()}
    inks = {i.id: i for i in InkRepository(session).all_sorted()}
    papers = {p.id: p for p in PaperRepository(session).all()}
    return samples, pens, inks, papers


# ── Varianten-/Dublettensuche ──────────────────────────────────────────────

def find_pen_variant(session: Any, brand: str, model: str,
                     color: Optional[str], capacity_ml: Optional[float]) -> Optional[Pen]:
    """CSV-Import-Match: exakte Modellvariante unabhängig vom Aktivstatus."""
    return PenRepository(session).find_variant(brand, model, color, capacity_ml)


def find_active_pen_duplicate(session: Any, data: Dict[str, Any]) -> Optional[Pen]:
    """Aktive Dublette für den Kopieren-/Anlegen-Fluss (gleiche Variante)."""
    return PenRepository(session).find_variant(
        data.get("brand"), data.get("model"), data.get("color"),
        data.get("ink_capacity_ml"), only_active=True,
    )


def single_active_pen_id(session: Any) -> Optional[int]:
    """Genau ein aktiver Füller → dessen ID, sonst None (Auswahl nötig)."""
    active = PenRepository(session).active()
    return active[0].id if len(active) == 1 else None


# ── Feder-Format & ähnliche Federn (Nib-Anlage aus dem Füllerdialog) ───────

def find_or_create_nib_format(session: Any, manufacturer: Optional[str],
                              physical_size: Optional[str],
                              is_proprietary: bool) -> Optional[int]:
    """Bestehendes NibFormat (normalisiert verglichen) nutzen oder anlegen.

    Rückgabe: format_id oder None, wenn weder Hersteller noch Größe angegeben.
    Legt bei Bedarf via ``session.add``/``flush`` an (Commit beim Aufrufer).
    """
    if not (manufacturer or physical_size):
        return None
    norm_mfr = normalize_text(manufacturer)
    norm_phys = normalize_text(physical_size)
    for fmt in NibFormatRepository(session).all():
        if (normalize_text(fmt.manufacturer) == norm_mfr
                and normalize_text(fmt.physical_size) == norm_phys
                and bool(fmt.is_proprietary) == bool(is_proprietary)):
            return fmt.id
    fmt = NibFormat(
        manufacturer=(manufacturer or "Unbekannt").strip(),
        physical_size=(physical_size or "").strip() or None,
        is_proprietary=bool(is_proprietary),
    )
    session.add(fmt)
    session.flush()
    return fmt.id


def find_similar_nib(session: Any, format_id: Optional[int],
                     nib_data: Dict[str, Any]):
    """Erste Feder gleichen Formats mit identischen Kernmerkmalen, sonst None."""
    for existing in NibRepository(session).by_format(format_id):
        same = (
            normalize_text(existing.size) == normalize_text(nib_data.get("size"))
            and normalize_text(existing.material) == normalize_text(nib_data.get("material"))
            and normalize_text(existing.grind) == normalize_text(nib_data.get("grind"))
            and normalize_text(existing.source) == normalize_text(nib_data.get("source"))
            and bool(existing.is_proprietary) == bool(nib_data.get("is_proprietary"))
        )
        if same:
            return existing
    return None


# ── Kaufpreis-Spiegelung in den Ausgaben-Tracker ───────────────────────────

def sync_purchase_expense_for_pen(session: Any, pen: Pen) -> None:
    """Füller-Kaufpreis als genau einen Auto-Eintrag im Tracker spiegeln.

    Preis ≤ 0 entfernt einen vorhandenen Auto-Eintrag; sonst wird er angelegt
    bzw. aktualisiert. Manuelle Ausgaben bleiben unberührt. (1:1 aus dem
    früheren ``ui.pen_widget._sync_purchase_expense_for_pen``.)
    """
    if not pen or not pen.id:
        return
    auto_tag = f"{AUTO_PURCHASE_TAG_PREFIX}{pen.id}"
    exp = ExpenseRepository(session).find_auto_purchase_for_pen(pen.id, auto_tag)
    price = pen.purchase_price or 0.0
    if price <= 0:
        if exp:
            session.delete(exp)
        return
    if not exp:
        exp = Expense(
            item_type="pen", pen_id=pen.id, shipping=0.0, customs=0.0,
            currency=getattr(pen, "purchase_currency", None) or LocaleService.instance().currency,
            notes=auto_tag,
        )
        session.add(exp)
    exp.amount = price
    exp.currency = getattr(pen, "purchase_currency", None) or LocaleService.instance().currency
    exp.purchase_date = pen.purchase_date
    exp.description = f"Kauf: {pen.brand} {pen.model}"
