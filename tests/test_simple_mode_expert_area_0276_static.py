"""v0.2.76: Simple Mode / Expert Area release guards."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_app_mode_helper_defines_simple_default_and_expert_pages():
    src = read("logic/app_mode.py")
    assert 'SIMPLE_MODE = "simple"' in src
    assert 'EXPERT_MODE = "expert"' in src
    assert 'SIMPLE_PAGES = {0, 1, 2, 5, 9, 10}' in src
    assert 'EXPERT_ONLY_PAGES = {3, 4, 6, 7, 8, 11, 12, 13}' in src
    assert 'fallback_page' in src


def test_navigation_has_simple_and_expert_group_orders_and_toggle():
    src = read("ui/navigation.py")
    assert "GROUPED_ORDER_SIMPLE" in src
    assert "GROUPED_ORDER_EXPERT" in src
    assert "modeChanged = Signal(str)" in src
    assert "switch_to_expert" in src
    assert "switch_to_simple" in src
    assert "set_app_mode" in src


def test_main_window_blocks_hidden_expert_pages_in_simple_mode():
    src = read("ui/main_window.py")
    assert "from logic.app_mode import fallback_page" in src
    assert "index = fallback_page(index)" in src
    assert "self.sidebar.modeChanged.connect" in src


def test_dashboard_exposes_four_primary_quick_actions():
    src = read("ui/dashboard_widget.py")
    assert "action_requested = Signal(int, str)" in src
    for key in [
        "dashboard.quick_actions.add_pen",
        "dashboard.quick_actions.add_ink",
        "dashboard.quick_actions.fill_pen",
        "dashboard.quick_actions.clean_pen",
    ]:
        assert key in src
    assert 'setObjectName("dashboardPrimaryAction")' in src


def test_gui_smoke_test_covers_simple_and_expert_modes():
    src = read("tools/gui_smoke_test.py")
    assert "SIMPLE_MODE" in src
    assert "EXPERT_MODE" in src
    assert "assert set(window.sidebar._buttons) == set(SIMPLE_PAGES)" in src
    assert "assert window._stack.currentIndex() == 0" in src


def test_i18n_has_new_mode_keys_in_all_languages():
    import json
    for lang in ("de", "en", "fr"):
        data = json.loads(read(f"i18n/{lang}.json"))
        assert data["nav"]["group_quickstart"]
        assert data["ui"]["navigation"]["switch_to_expert"]
        assert data["ui"]["navigation"]["switch_to_simple"]
        assert data["settings"]["mode_label"]
        assert data["dashboard"]["quick_actions"]["add_pen"]
