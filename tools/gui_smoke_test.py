#!/usr/bin/env python3
"""Lightweight Qt GUI smoke test for release candidates.

This is not a replacement for the manual Windows/Linux checklist in docs/, but it
catches the most common release blockers: missing Qt runtime, broken imports,
window construction failure, page navigation crashes and basic i18n loading.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    # Keep smoke data away from the user's real collection unless explicitly set.
    temp_dir = tempfile.TemporaryDirectory(prefix="fpm_gui_smoke_")
    if "FPM_DATA_DIR" not in os.environ:
        os.environ["FPM_DATA_DIR"] = temp_dir.name
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    try:
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication
    except ModuleNotFoundError as exc:
        print(f"SKIP: PySide6/runtime package missing: {exc.name}")
        return 77

    try:
        from database.db import init_db
        from i18n.translator import Translator, load_language_from_settings
        from i18n.qt_i18n import install_qt_i18n_hooks
        from ui.main_window import MainWindow
        from logic.app_mode import EXPERT_MODE, SIMPLE_MODE, SIMPLE_PAGES, set_app_mode
        from ui.tour_controller import build_steps, should_show_tour
        from ui.styles import get_stylesheet
        from ui.ui_scale import apply_ui_scaling
    except Exception as exc:
        print(f"FAIL: import/startup module error: {exc}")
        return 1

    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(get_stylesheet())
    apply_ui_scaling(app)
    init_db()
    load_language_from_settings()
    install_qt_i18n_hooks()

    tr = Translator.instance()
    for lang in ("de", "en", "fr"):
        tr.set_language(lang)
        assert tr.t("nav.dashboard") != "nav.dashboard"
        assert tr.t("rotation.msg_fill_success") != "rotation.msg_fill_success"

    # Frische Sammlung: erst Modulrunde (Expertenteil am Schluss), dann echte Datenanlage.
    assert should_show_tour() is True
    tour_steps = build_steps()
    ids = [step.step_id for step in tour_steps]
    assert [step.page_index for step in tour_steps if step.on_next is not None][:2] == [2, 1]
    assert ids.index("expert_intro") < ids.index("setup_intro") < ids.index("ink_add")
    assert ids.index("ink_add") < ids.index("pen_add") < ids.index("rotation_generate")
    assert {3, 4, 6, 7, 8, 11, 12, 13} <= {
        step.page_index for step in tour_steps if step.mode == "expert"
    }

    # Simple Mode is the DAU default: expert-only pages must not be reachable by accident.
    set_app_mode(SIMPLE_MODE)
    window = MainWindow()
    window.show()
    assert set(window.sidebar._buttons) == set(SIMPLE_PAGES)
    window._navigate(8)  # rules are expert-only; should fall back to dashboard
    assert window._stack.currentIndex() == 0

    # Expert Mode must still expose and instantiate every module.
    set_app_mode(EXPERT_MODE)
    window.sidebar._setup_ui()
    window._navigation_mode_changed(EXPERT_MODE)
    for page in range(14):
        window._navigate(page)  # intentional smoke hook: exercises lazy page creation
        assert window._stack.currentIndex() == page
        app.processEvents()

    # Reale Schnellaktion: sie muss Vorschläge erzeugen, nicht nur die Seite aktualisieren.
    from database.db import get_session
    from database.models import Ink, Pen
    session = get_session()
    try:
        session.add(Ink(brand="Smoke", name="Blue", color_family="blue", color_hex="#24518a"))
        session.add(Pen(brand="Smoke", model="Pen", fill_system="converter"))
        session.commit()
    finally:
        session.close()
    window._run_page_action(5, "generate_suggestions")
    rotation = window._ensure_widget(5)
    assert rotation._last_suggestions
    assert rotation.sug_table.rowCount() >= 1

    QTimer.singleShot(50, app.quit)
    app.exec()
    print("OK: GUI smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
