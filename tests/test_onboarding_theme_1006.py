"""Regression fuer v1.0.6: Einfuehrung muss dem aktiven Theme folgen."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_tour_bubble_hat_keine_eigenen_farb_styles_mehr():
    source = (ROOT / "ui" / "tour_overlay.py").read_text(encoding="utf-8")
    # Bubble/Buttons werden ueber ui/styles.py und damit aus Theme-Rollen gestylt.
    assert ".setStyleSheet(" not in source
    for object_name in (
        "tourBubble", "tourTitle", "tourBody", "tourSkipButton",
        "tourBackButton", "tourNextButton", "tourAbortButton",
    ):
        assert object_name in source


def test_spotlight_painter_nimmt_theme_farben():
    source = (ROOT / "ui" / "tour_overlay.py").read_text(encoding="utf-8")
    assert 'theme.color("akzent")' in source
    assert 'theme.color("hintergrund_seitenleiste")' in source
    assert "HALO_COLOR" not in source
    assert "DIM_COLOR" not in source


def test_legacy_onboarding_verwendet_nur_theme_qss():
    source = (ROOT / "ui" / "onboarding_wizard.py").read_text(encoding="utf-8")
    assert ".setStyleSheet(" not in source
    for object_name in (
        "onboardingProgress", "onboardingStepLabel", "onboardingTitle",
        "onboardingBody", "onboardingActionButton", "onboardingSkipButton",
        "onboardingBackButton", "onboardingNextButton",
    ):
        assert object_name in source


def test_global_stylesheet_deckt_tour_und_onboarding_ab():
    source = (ROOT / "ui" / "styles.py").read_text(encoding="utf-8")
    for selector in (
        "QFrame#tourBubble", "QLabel#tourTitle", "QLabel#tourBody",
        "QPushButton#tourSkipButton", "QPushButton#tourBackButton",
        "QPushButton#tourNextButton", "QPushButton#tourAbortButton",
        "QProgressBar#onboardingProgress", "QLabel#onboardingTitle",
        "QLabel#onboardingBody", "QPushButton#onboardingActionButton",
        "QPushButton#onboardingNextButton",
    ):
        assert selector in source
    # Die entscheidenden Rollen muessen im Abschnitt vorkommen.
    assert 'c("karte_hintergrund")' in source
    assert 'c("text")' in source
    assert 'c("akzent")' in source
    assert 'c("erfolg")' in source
    assert 'c("gefahr")' in source
