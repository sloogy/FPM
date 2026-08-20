"""Runtime and static guards for the v0.2.98 UI/usability hardening."""
from __future__ import annotations

import os
import re
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout

from ui.common import ResponsiveDialog
from ui.dashboard_widget import DashboardWidget
from ui.settings_widget import ResponsiveButtonGrid, SettingsWidget


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_responsive_dialog_is_scrollable_and_screen_bounded(qapp):
    dialog = ResponsiveDialog()
    root = QVBoxLayout(dialog)
    for index in range(20):
        root.addWidget(QLabel(f"Row {index}"))
    dialog.enable_responsive_layout(
        2400,
        1600,
        minimum_width=1200,
        minimum_height=1000,
        scroll=True,
    )
    dialog.show()
    qapp.processEvents()
    try:
        available = dialog.screen().availableGeometry()
        assert dialog.maximumWidth() <= available.width() - 16
        assert dialog.maximumHeight() <= available.height() - 16
        assert dialog.minimumWidth() <= dialog.maximumWidth()
        assert dialog.minimumHeight() <= dialog.maximumHeight()
        assert dialog._responsive_scroll is not None
        assert dialog._responsive_scroll.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAsNeeded
    finally:
        dialog.close()


def test_settings_switch_to_compact_navigation_on_narrow_width(qapp, tmp_path):
    from database.db import init_db
    init_db(tmp_path / "settings.db")
    widget = SettingsWidget()
    widget.show()
    try:
        widget.resize(800, 600)
        qapp.processEvents()
        assert widget.settings_nav_combo.isVisible()
        assert not widget.settings_nav.isVisible()
        widget.settings_nav_combo.setCurrentIndex(3)
        qapp.processEvents()
        assert widget.settings_stack.currentIndex() == 3
        assert widget.settings_nav.currentRow() == 3

        widget.resize(980, 700)
        qapp.processEvents()
        assert widget.settings_nav.isVisible()
        assert not widget.settings_nav_combo.isVisible()
        assert widget.settings_nav.currentRow() == 3
    finally:
        widget.close()


def test_responsive_button_grid_reflows(qapp):
    panel = ResponsiveButtonGrid()
    buttons = [QPushButton(str(i)) for i in range(5)]
    for button in buttons:
        panel.add_button(button)
    panel.show()
    try:
        panel.resize(360, 300)
        qapp.processEvents()
        assert panel._grid.getItemPosition(panel._grid.indexOf(buttons[1]))[:2] == (1, 0)
        panel.resize(900, 300)
        qapp.processEvents()
        assert panel._grid.getItemPosition(panel._grid.indexOf(buttons[1]))[:2] == (0, 1)
        assert panel._grid.getItemPosition(panel._grid.indexOf(buttons[2]))[:2] == (0, 2)
    finally:
        panel.close()


def test_dashboard_tiles_have_visible_open_button(qapp):
    widget = DashboardWidget()
    pages: list[int] = []
    widget.navigate_to.connect(pages.append)
    widget.resize(900, 700)
    widget.show()
    qapp.processEvents()
    try:
        assert all(tile.open_button.isVisible() for tile in widget._tiles if not tile.isHidden())
        assert all("dashboard.tiles." not in tile.open_button.text() for tile in widget._tiles)
        # Nach dem ersten echten Layoutlauf darf das Dashboard nicht im
        # fälschlichen Einspaltenmodus hängen bleiben.
        second = widget._quick_buttons[1]
        assert widget._quick_buttons_layout.getItemPosition(
            widget._quick_buttons_layout.indexOf(second)
        )[:2] == (0, 1)
        QTest.mouseClick(widget._tile_service.open_button, Qt.MouseButton.LeftButton)
        qapp.processEvents()
        assert pages == [1]
        assert widget._expanded_detail is None
    finally:
        widget.close()


def test_secondary_text_palette_meets_normal_text_contrast_target():
    def luminance(hex_color: str) -> float:
        values = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in values]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    fg = luminance("#5f6f72")
    bg = luminance("#ffffff")
    ratio = (max(fg, bg) + 0.05) / (min(fg, bg) + 0.05)
    assert ratio >= 4.5

    # Low-contrast shades may still be used for controls/backgrounds, but no
    # longer as explicit normal-text colors in production UI code.
    for path in Path("ui").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"(?<!-)color\s*:\s*#(?:7f8c8d|95a5a6)\b", text, re.I), path


def test_large_dialogs_use_central_responsive_base():
    required = {
        "ui/pen_dialogs.py": ["PenDialog", "SizeCompareDialog", "ServiceBlockDialog", "LoadInkDialog"],
        "ui/ink_widget.py": ["InkDialog"],
        "ui/nib_widget.py": ["NibDialog"],
        "ui/paper_widget.py": ["PaperDialog"],
        "ui/writing_samples_widget.py": ["WritingSampleDialog", "WritingSampleComparisonDialog"],
        "ui/rules_widget.py": ["RuleDialog"],
        "ui/update_dialog.py": ["UpdateDialog"],
    }
    for file_name, classes in required.items():
        source = Path(file_name).read_text(encoding="utf-8")
        for class_name in classes:
            assert f"class {class_name}(ResponsiveDialog):" in source
        assert "enable_responsive_layout" in source


def test_database_lifecycle_closes_engine_and_session_factory(tmp_path):
    import database.db as db

    db.init_db(tmp_path / "lifecycle.db")
    session = db.get_session()
    assert db.engine is not None
    assert db.SessionLocal is not None
    # close_db muss auch bei einer noch existierenden Session gefahrlos sein.
    db.close_db()
    assert db.engine is None
    assert db.SessionLocal is None
    db.close_db()  # idempotent
    session.close()
