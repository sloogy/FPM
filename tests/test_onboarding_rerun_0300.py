"""Regression guards for v0.3.00 onboarding rerun and enterprise merge."""
from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

import database.db as db
from database.models import AppSettings
from ui.onboarding_wizard import mark_wizard_done, should_show_wizard
from ui.tour_controller import mark_tour_done, reset_tour, should_show_tour

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def isolated_db(tmp_path):
    db.init_db(tmp_path / "onboarding.db")
    yield
    db.close_db()


def _flags() -> tuple[str, str]:
    session = db.get_session()
    try:
        return (
            str(AppSettings.get(session, "onboarding_completed", "0")),
            str(AppSettings.get(session, "onboarding_force_next_start", "0")),
        )
    finally:
        session.close()


def test_reset_forces_tour_and_fallback_wizard_despite_seeded_data():
    # init_db seeds example inks. The explicit reset must override that data check.
    session = db.get_session()
    try:
        AppSettings.set(session, "onboarding_completed", "1")
        AppSettings.set(session, "onboarding_force_next_start", "0")
    finally:
        session.close()

    reset_tour()

    assert _flags() == ("0", "1")
    assert should_show_tour() is True
    assert should_show_wizard() is True


def test_tour_completion_clears_force_flag():
    reset_tour()
    mark_tour_done()

    assert _flags() == ("1", "0")
    assert should_show_tour() is False


def test_wizard_completion_clears_force_flag():
    reset_tour()
    mark_wizard_done()

    assert _flags() == ("1", "0")
    assert should_show_wizard() is False


def test_settings_can_request_wizard_without_touching_collection(qapp):
    from ui.settings_widget import SettingsWidget

    widget = SettingsWidget()
    requested: list[bool] = []
    widget.wizard_requested.connect(lambda: requested.append(True))
    try:
        widget._start_wizard_now()
        qapp.processEvents()
        assert requested == [True]
    finally:
        widget.close()


def test_main_window_uses_one_shared_wizard_codepath():
    source = (ROOT / "ui" / "main_window.py").read_text(encoding="utf-8")
    assert source.count("OnboardingWizard(self)") == 1
    assert "def start_onboarding_wizard" in source
    assert "wizard_sig.connect(self.start_onboarding_wizard)" in source
    assert "self.start_onboarding_wizard()" in source


def test_wizard_labels_exist_in_all_languages():
    for language in ("de", "en", "fr"):
        data = json.loads((ROOT / "i18n" / f"{language}.json").read_text(encoding="utf-8"))
        triggers = data["tour"]["triggers"]
        assert triggers["wizard_button"].strip()
        assert triggers["wizard_tooltip"].strip()
