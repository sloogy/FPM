"""v0.2.77: Funktionale Guards für Simple/Expert-Modus und Schnellaktionen.

Ergänzt die statischen 0.2.76-Tests um ausführbare Logik-Checks (headless,
``logic.app_mode`` ist dank Lazy-Imports ohne DB/Qt importierbar) und sichert
den Fix der stummen Befüllen-/Reinigen-Schnellaktionen ab.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


# ── Modus-Logik funktional (nicht nur statisch) ───────────────────
def test_fallback_page_routes_hidden_pages_to_dashboard():
    from logic.app_mode import fallback_page
    # Versteckte Expertenseiten fallen im Simple Mode aufs Dashboard zurück …
    for hidden in (3, 4, 6, 7, 8, 11, 12, 13):
        assert fallback_page(hidden, "simple") == 0, hidden
    # … sichtbare Kernseiten bleiben erhalten …
    for visible in (0, 1, 2, 5, 9, 10):
        assert fallback_page(visible, "simple") == visible, visible
    # … und im Expertenmodus wird nie umgeleitet.
    for page in range(14):
        assert fallback_page(page, "expert") == page, page


def test_page_visible_matches_simple_pages_set():
    from logic.app_mode import SIMPLE_PAGES, page_visible
    for page in range(14):
        assert page_visible(page, "simple") == (page in SIMPLE_PAGES), page
        assert page_visible(page, "expert") is True, page


def test_normalize_app_mode_is_defensive():
    from logic.app_mode import normalize_app_mode
    assert normalize_app_mode(None) == "simple"
    assert normalize_app_mode("  EXPERT ") == "expert"
    assert normalize_app_mode("banana") == "simple"


def test_simple_and_expert_pages_partition_all_modules():
    from logic.app_mode import SIMPLE_PAGES, EXPERT_ONLY_PAGES
    import ast
    # ui.navigation importiert Qt – hier ohne PySide6 per AST auswerten.
    tree = ast.parse(_read("ui/navigation.py"))
    modules = grouped_simple = None
    for node in ast.walk(tree):
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets = [node.target]  # z. B. MODULES: Dict[str, dict] = {...}
        for tgt in targets:
            name = getattr(tgt, "id", "")
            if name == "MODULES":
                modules = ast.literal_eval(node.value)
            elif name == "GROUPED_ORDER_SIMPLE":
                grouped_simple = ast.literal_eval(node.value)
    assert modules and grouped_simple, "MODULES/GROUPED_ORDER_SIMPLE nicht gefunden"
    all_pages = {int(m["page"]) for m in modules.values()}
    assert SIMPLE_PAGES | EXPERT_ONLY_PAGES == all_pages
    assert not (SIMPLE_PAGES & EXPERT_ONLY_PAGES)
    simple_nav_pages = {
        int(modules[mid]["page"]) for _g, mids in grouped_simple for mid in mids
    }
    # Die Simple-Sidebar zeigt exakt die als sichtbar definierten Seiten.
    assert simple_nav_pages == SIMPLE_PAGES


# ── Fix: Schnellaktionen dürfen ohne Selektion nicht stumm enden ──
def test_quick_actions_use_quick_pen_helper():
    src = _read("ui/pen_widget.py")
    assert "def _quick_pen_id(self)" in src
    # Beide Aktionen laufen über den Helfer statt still zu returnen.
    assert src.count("pen_id = self._quick_pen_id()") == 2
    # Autowahl bei genau einem aktiven Füller + freundlicher Hinweis sonst.
    assert "filter_by(is_active=True).all()" in src
    assert "ui.pen_widget.quick_select_pen_hint" in src


def test_quick_hint_keys_present_in_all_languages():
    keys = [
        "ui.pen_widget.quick_no_selection_title",
        "ui.pen_widget.quick_select_pen_hint",
    ]
    for lg in ("de", "en", "fr"):
        d = json.loads((ROOT / "i18n" / f"{lg}.json").read_text(encoding="utf-8"))
        for dotted in keys:
            cur = d
            for part in dotted.split("."):
                assert isinstance(cur, dict) and part in cur, f"{lg}:{dotted}"
                cur = cur[part]
            assert isinstance(cur, str) and cur.strip(), f"{lg}:{dotted}"
