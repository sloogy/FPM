"""Regression checks for Wishlist → purchased collection transfer.

These tests are intentionally source-level because the CI/runtime used for the
logic tests does not install PySide6/SQLAlchemy. They guard the exact regression
that bought wishlist pens must become active collection pens and refresh the Pen UI.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_pen_widget_listens_to_external_pen_changes():
    src = (ROOT / "ui" / "pen_widget.py").read_text(encoding="utf-8")
    assert "bus.pens_changed.connect(self.refresh)" in src


def test_wishlist_pen_transfer_creates_visible_active_pen():
    src = (ROOT / "ui" / "wishlist_widget.py").read_text(encoding="utf-8")
    assert "is_active=True" in src
    assert 'availability_status="available"' in src
    assert "rotation_blocked=False" in src
    assert 'rotation_role="writer"' in src


def test_edit_status_bought_uses_transfer_workflow_not_silent_status_only():
    src = (ROOT / "ui" / "wishlist_widget.py").read_text(encoding="utf-8")
    assert "requested_bought =" in src
    assert "WishlistTransferDialog(self, item)" in src
    assert "self._apply_purchase_transfer(s, item, target)" in src


def test_wishlist_widget_imports_all_button_styles_it_uses():
    """Ein benutzter, aber nicht importierter Stil waere ein NameError im Klick.

    Geprueft wird der Namensraum des Moduls, nicht der Wortlaut der
    Importzeile - sonst bricht der Test bei jeder Umbenennung, ohne dass etwas
    kaputt waere.
    """
    import re

    import ui.wishlist_widget as widget

    src = (ROOT / "ui" / "wishlist_widget.py").read_text(encoding="utf-8")
    used = set(re.findall(r"\bbtn_[a-z_]+(?=\()", src))
    assert used, "Das Widget nutzt keine Stilfunktion mehr - Test veraltet?"
    missing = sorted(name for name in used if not hasattr(widget, name))
    assert not missing, f"nicht importiert: {missing}"


def test_wishlist_purchase_refreshes_budgetmanager_bridge_outbox():
    src = (ROOT / "ui" / "wishlist_widget.py").read_text(encoding="utf-8")
    assert "def _sync_budget_bridge_after_purchase" in src
    assert "self._sync_budget_bridge_after_purchase(s)" in src
    # Die sichere Variante, nicht die strikte: der Aufruf steht hinter dem
    # Commit. Wuerde er werfen, liefe er in den umgebenden except-Zweig und der
    # Nutzer saehe einen Fehler samt wirkungslosem Rollback, obwohl die
    # Uebernahme laengst gespeichert ist.
    assert "sync_default_outbox_from_session_safely(session)" in src
