"""Statische Guards für die v0.2.69-UX: Rechtsklick-Menüs und aufgeräumtes Dashboard.

Diese Tests brauchen kein PySide6-Runtime. Sie prüfen die Quelltext-Verdrahtung,
damit die neuen Bedienelemente nicht versehentlich wieder entfernt werden.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


# ── Dashboard: Rechtsklick + Navigations-Signal ───────────────────
def test_dashboard_has_navigate_signal_and_context_menus():
    src = _read("ui/dashboard_widget.py")
    assert "navigate_to = Signal(int)" in src
    assert src.count("setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)") >= 4
    assert "_table_menu" in src
    # Sprung-Navigation zu Füller- und Tinten-Seite
    assert "self.navigate_to.emit(1)" in src
    assert "self.navigate_to.emit(2)" in src


def test_dashboard_hides_empty_sections():
    src = _read("ui/dashboard_widget.py")
    for group in ("_timer_group", "_lock_group", "_health_group", "_activity_group"):
        assert f"self.{group}.setVisible(" in src, group
    assert "self._all_clear.setVisible(" in src


def test_dashboard_context_menu_guards_dismiss():
    # Schutz vor der None-is-None-Falle: nach exec muss auf None geprüft werden.
    src = _read("ui/dashboard_widget.py")
    idx = src.index("chosen = menu.exec(")
    tail = src[idx:idx + 200]
    assert "if chosen is None:" in tail


# ── Hauptfenster verbindet das Navigations-Signal ─────────────────
def test_main_window_wires_navigate_to():
    src = _read("ui/main_window.py")
    assert 'getattr(widget, "navigate_to"' in src
    assert "nav_sig.connect(self._navigate)" in src


# ── Schreibproben: Rechtsklick ────────────────────────────────────
def test_writing_samples_has_context_menu():
    src = _read("ui/writing_samples_widget.py")
    assert "customContextMenuRequested.connect(self._context_menu)" in src
    assert "def _context_menu(self, pos)" in src


# ── Enthusiast-Lab: Rechtsklick auf Tinten-Tabelle ────────────────
def test_enthusiast_lab_has_ink_context_menu():
    src = _read("ui/enthusiast_lab_widget.py")
    assert "navigate_to = Signal(int)" in src
    assert "customContextMenuRequested.connect(self._ink_context_menu)" in src
    assert "def _ink_context_menu(self, pos)" in src


# ── Merge v0.2.70: Leerzustände & Button-Konsistenz ───────────────
def test_wishlist_and_expenses_have_empty_state():
    for rel in ("ui/wishlist_widget.py", "ui/expenses_widget.py"):
        src = _read(rel)
        assert "from ui.common import EmptyStateWidget" in src, rel
        assert "QStackedWidget" in src, rel
        assert "self.stack.setCurrentIndex(1" in src, rel


def test_add_buttons_are_consistent():
    import json
    keys = [
        "ui.pen_widget.fuller_0c6e26b0",
        "ui.ink_widget.tinte_hinzufugen_988b4827",
        "ui.nib_widget.feder_hinzufugen_f3956c58",
        "ui.paper_widget.papier_hinzufugen_986b4afe",
        "ui.wishlist_widget.wunsch_bd625c0d",
        "ui.expenses_widget.ausgabe_c7d8b984",
        "ui.rules_widget.regel_81add3ac",
    ]
    d = json.loads((ROOT / "i18n" / "de.json").read_text(encoding="utf-8"))
    for dotted in keys:
        cur = d
        for part in dotted.split("."):
            cur = cur[part]
        # Einheitliches Muster: "+ <Objekt> hinzufügen"
        assert cur.startswith("+ ") and cur.endswith(" hinzufügen"), f"{dotted}={cur!r}"


def test_empty_state_keys_present_all_languages():
    import json
    keys = [
        "ui.wishlist_widget.empty_title", "ui.wishlist_widget.empty_subtitle",
        "ui.wishlist_widget.empty_action", "ui.expenses_widget.empty_title",
        "ui.expenses_widget.empty_subtitle", "ui.expenses_widget.empty_action",
    ]
    for lg in ("de", "en", "fr"):
        d = json.loads((ROOT / "i18n" / f"{lg}.json").read_text(encoding="utf-8"))
        for dotted in keys:
            cur = d
            for part in dotted.split("."):
                assert isinstance(cur, dict) and part in cur, f"{lg}:{dotted}"
                cur = cur[part]
            assert isinstance(cur, str) and cur.strip(), f"{lg}:{dotted}"


def test_dashboard_context_keys_present_in_all_languages():
    import json
    keys = [
        "dashboard.all_clear",
        "dashboard.context.jump_to_pen",
        "dashboard.context.jump_to_ink",
        "dashboard.context.copy_details",
        "dashboard.context.refresh",
    ]
    for lg in ("de", "en", "fr"):
        d = json.loads((ROOT / "i18n" / f"{lg}.json").read_text(encoding="utf-8"))
        for dotted in keys:
            cur = d
            for part in dotted.split("."):
                assert isinstance(cur, dict) and part in cur, f"{lg}:{dotted}"
                cur = cur[part]
            assert isinstance(cur, str) and cur.strip(), f"{lg}:{dotted} empty"
