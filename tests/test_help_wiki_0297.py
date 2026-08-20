"""v0.2.97 regression tests for searchable multilingual help and safe drafts."""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QTabWidget

from i18n.translator import Translator
from ui.help_widget import HelpWidget
from ui.pen_widget import PenDialog

APP = QApplication.instance() or QApplication([])


def _dispose(widget) -> None:
    widget.close()
    widget.deleteLater()
    APP.processEvents()


def test_help_search_filters_cards_and_selects_matching_tab():
    Translator.instance().set_language("de")
    widget = HelpWidget()
    try:
        assert widget.tabs.count() == 9
        widget.search_edit.setText("Vac Shimmer")
        APP.processEvents()
        assert not widget.search_status.isHidden()
        assert widget.search_status.text()[0].isdigit()
        assert widget.tabs.isTabVisible(HelpWidget.TOPICS["rules"])
    finally:
        _dispose(widget)


def test_help_search_no_result_and_topic_jump_are_stable():
    Translator.instance().set_language("en")
    widget = HelpWidget()
    try:
        widget.search_edit.setText("term-that-does-not-exist-anywhere")
        APP.processEvents()
        assert not widget.search_status.isHidden()
        assert "No matching" in widget.search_status.text()

        widget.show_topic("data_entry")
        assert widget.search_edit.text() == ""
        assert widget.tabs.currentIndex() == HelpWidget.TOPICS["data_entry"]
        assert all(widget.tabs.isTabVisible(i) for i in range(widget.tabs.count()))
    finally:
        _dispose(widget)


def test_manual_candidate_matches_selected_language():
    tr = Translator.instance()
    expected = {
        "de": "BENUTZERHANDBUCH_DE.md",
        "en": "USER_MANUAL_EN.md",
        "fr": "MANUEL_UTILISATEUR_FR.md",
    }
    for language, filename in expected.items():
        tr.set_language(language)
        candidates = HelpWidget._manual_candidates()
        assert candidates[0].name == filename
        assert candidates[0].is_file()


def test_pen_dialog_detects_modified_draft_without_losing_values(tmp_path):
    Translator.instance().set_language("de")
    from database.db import init_db

    init_db(tmp_path / "help-wiki-test.db")
    dialog = PenDialog()
    try:
        assert not dialog._has_unsaved_changes()
        dialog.brand_edit.setText("Pelikan")
        dialog.model_edit.setText("M800")
        dialog.len_spin.setValue(141.5)
        tabs = dialog.findChild(QTabWidget)
        assert tabs is not None
        for index in range(tabs.count()):
            tabs.setCurrentIndex(index)
            APP.processEvents()

        assert dialog._has_unsaved_changes()
        assert dialog.brand_edit.text() == "Pelikan"
        assert dialog.model_edit.text() == "M800"
        assert dialog.len_spin.value() == 141.5
    finally:
        _dispose(dialog)
