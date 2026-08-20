"""v0.2.96 runtime guards for the focus-tile dashboard."""
from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from ui.dashboard_widget import DashboardWidget


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _dashboard(qapp: QApplication) -> DashboardWidget:
    widget = DashboardWidget()
    widget.resize(920, 700)
    widget.show()
    qapp.processEvents()
    return widget


def test_tiles_start_compact_and_details_are_exclusive(qapp):
    widget = _dashboard(qapp)
    try:
        assert widget._tiles_grid.count() == 4  # budget tile is conditional
        assert widget._expanded_detail is None
        assert not any(group.isVisible() for group in widget._detail_groups.values())

        widget._toggle_detail("rotation")
        qapp.processEvents()
        assert widget._timer_group.isVisible()
        assert widget.timer_table.hasFocus()
        assert widget._tile_rotation._selected is True

        widget._toggle_detail("collection")
        qapp.processEvents()
        assert widget._health_group.isVisible()
        assert not widget._timer_group.isVisible()
        assert widget._tile_collection._selected is True
        assert widget._tile_rotation._selected is False

        widget._toggle_detail("collection")
        qapp.processEvents()
        assert widget._expanded_detail is None
        assert not widget._health_group.isVisible()
    finally:
        widget.close()


def test_tile_double_click_navigates_without_delayed_single_click(qapp):
    widget = _dashboard(qapp)
    pages: list[int] = []
    widget.navigate_to.connect(pages.append)
    try:
        QTest.mouseDClick(
            widget._tile_service,
            Qt.MouseButton.LeftButton,
            pos=QPoint(20, 20),
        )
        QTest.qWait(QApplication.doubleClickInterval() + 30)
        qapp.processEvents()
        assert pages == [1]
        assert widget._expanded_detail is None
    finally:
        widget.close()


def test_table_double_click_uses_section_target(qapp):
    widget = _dashboard(qapp)
    pages: list[int] = []
    widget.navigate_to.connect(pages.append)
    try:
        widget.activity_table.setRowCount(1)
        widget._toggle_detail("activity")
        qapp.processEvents()
        widget.activity_table.cellDoubleClicked.emit(0, 0)
        qapp.processEvents()
        assert pages == [5]
    finally:
        widget.close()
