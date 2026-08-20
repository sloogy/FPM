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

    # v0.3.02: Minimaldaten, damit Dashboard-Service, Timer- und Sperr-Pfade
    # nicht nur gegen eine leere Datenbank rauchen.
    from datetime import datetime, timedelta
    from database.db import get_session
    from database.models import Ink, InkLoad, Pen
    session = get_session()
    try:
        ink = Ink(brand="Smoke", name="Blue", color_hex="#123456",
                  color_family="blue", bottle_size_ml=50.0, remaining_ml=30.0)
        pen_ok = Pen(brand="Smoke", model="Writer", fill_system="converter",
                     purchase_price=100.0, purchase_currency="CHF")
        pen_blocked = Pen(brand="Smoke", model="Blocked", fill_system="piston",
                          rotation_blocked=True)
        session.add_all([ink, pen_ok, pen_blocked])
        session.flush()
        session.add(InkLoad(pen_id=pen_ok.id, ink_id=ink.id,
                            loaded_date=datetime.now() - timedelta(days=45)))
        session.commit()
    finally:
        session.close()

    tr = Translator.instance()
    for lang in ("de", "en", "fr"):
        tr.set_language(lang)
        assert tr.t("nav.dashboard") != "nav.dashboard"
        assert tr.t("rotation.msg_fill_success") != "rotation.msg_fill_success"

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

    # v0.3.02: Dashboard-Refresh explizit mit gefüllten Daten (Service-Pfad,
    # Timer überfällig, Sperr-Zeile) und Konstruktions-Smoke aller fünf
    # ausgelagerten Füller-Dialoge – fängt Split-/Importfehler in der CI.
    window._navigate(0)
    dashboard = window._stack.widget(0)
    dashboard.refresh()
    assert dashboard.timer_table.rowCount() >= 1, "Überfällige Ladung fehlt im Timer"
    assert dashboard.service_table.rowCount() >= 1, "Gesperrter Füller fehlt in Service"

    from ui.pen_dialogs import (LoadInkDialog, PenDialog, ServiceBlockDialog,
                                ServiceHelpDialog, SizeCompareDialog)
    from database.db import get_session as _gs
    _s = _gs()
    try:
        smoke_pen = _s.query(Pen).filter_by(model="Writer").first()
        smoke_pen_id = smoke_pen.id if smoke_pen else None
    finally:
        _s.close()
    for dlg in (
        PenDialog(window),
        LoadInkDialog(window, smoke_pen_id),
        SizeCompareDialog(window),
        ServiceBlockDialog(window),
        ServiceHelpDialog(window, "piston"),
    ):
        dlg.deleteLater()
    app.processEvents()

    QTimer.singleShot(50, app.quit)
    app.exec()
    print("OK: GUI smoke test passed (dialog + dashboard data paths included)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
