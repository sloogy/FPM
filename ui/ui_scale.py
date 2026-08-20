"""Zentrale, Qt-konforme UI-Skalierung.

Qt liefert Geometrien bereits in logischen Pixeln. Deshalb darf die
Anwendung den Qt-DPI-Faktor nicht ein zweites Mal auf Schrift und Größen
multiplizieren. Die App-Skalierung ist nur eine zusätzliche
Benutzer-/Lesbarkeitsstufe.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Optional

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication


@dataclass(frozen=True)
class ScalePreset:
    key: str
    label: str
    factor: float


PRESETS: list[ScalePreset] = [
    ScalePreset("auto", "Auto – Fenster und Bildschirm", 1.0),
    ScalePreset("compact", "Kompakt", 0.90),
    ScalePreset("normal", "Normal", 1.00),
    ScalePreset("laptop", "Laptop groß", 1.12),
    ScalePreset("large", "Sehr groß", 1.28),
]

_CURRENT_FACTOR = 1.0
_PATCH_INSTALLED = False
_ORIGINAL_SET_STYLESHEET = None


def _scale_inline_css(css: str, factor: float) -> str:
    """Skaliert nur dimensionsbezogene px-Werte in Inline-QSS."""
    if not css or abs(factor - 1.0) < 0.03:
        return css
    properties = (
        "font-size", "padding", "margin", "min-height", "max-height",
        "min-width", "max-width", "border-radius", "width", "height",
        "spacing", "left", "right", "top", "bottom",
    )
    pattern = "|".join(re.escape(prop) for prop in properties)

    def replace(match: re.Match[str]) -> str:
        value = max(1, round(float(match.group(2)) * factor))
        return f"{match.group(1)}{value}px"

    return re.sub(rf"((?:{pattern})\s*:\s*)(\d+(?:\.\d+)?)px", replace, css)


def install_inline_stylesheet_scaler() -> None:
    global _PATCH_INSTALLED, _ORIGINAL_SET_STYLESHEET
    if _PATCH_INSTALLED:
        return
    try:
        from PySide6.QtWidgets import QWidget

        _ORIGINAL_SET_STYLESHEET = QWidget.setStyleSheet

        def patched(widget, stylesheet: str) -> None:
            _ORIGINAL_SET_STYLESHEET(
                widget, _scale_inline_css(stylesheet or "", _CURRENT_FACTOR)
            )

        QWidget.setStyleSheet = patched
        _PATCH_INSTALLED = True
    except Exception:
        # Skalierung darf den Programmstart nie blockieren.
        return


def preset_factor(mode: str | None) -> float:
    normalized = (mode or "auto").strip().lower()
    return next((p.factor for p in PRESETS if p.key == normalized), 1.0)


def _screen_auto_factor(app: QApplication) -> float:
    """Zusatzskalierung anhand der *logischen* Arbeitsfläche.

    Kein ``logicalDotsPerInch()/96``: Qt hat diesen Faktor bereits angewandt.
    Kleine Arbeitsflächen werden kompakter statt größer, damit Fenstermodus
    und Dialoge vollständig bedienbar bleiben.
    """
    screen = app.primaryScreen()
    if screen is None:
        return 1.0
    geometry = screen.availableGeometry()
    width, height = geometry.width(), geometry.height()
    if width < 1100 or height < 720:
        return 0.88
    if width < 1360 or height < 820:
        return 0.94
    if width >= 2200 and height >= 1250:
        return 1.08
    return 1.0


def current_scale_factor(
    app: Optional[QApplication] = None, mode: str | None = None
) -> float:
    app = app or QApplication.instance()
    if app is None:
        return preset_factor(mode)
    normalized = (mode or "auto").strip().lower()
    return _screen_auto_factor(app) if normalized == "auto" else preset_factor(normalized)


def _load_mode_from_settings(default: str = "auto") -> str:
    try:
        from database.db import get_session
        from database.models import AppSettings

        session = get_session()
        try:
            return AppSettings.get(session, "ui_scale_mode", default) or default
        finally:
            session.close()
    except Exception:
        return default


def apply_ui_scaling(
    app: Optional[QApplication] = None, mode: str | None = None
) -> float:
    """Wendet die zusätzliche App-Skalierung global an."""
    app = app or QApplication.instance()
    if app is None:
        return 1.0
    mode = _load_mode_from_settings() if mode is None else mode

    global _CURRENT_FACTOR
    _CURRENT_FACTOR = current_scale_factor(app, mode)
    install_inline_stylesheet_scaler()

    font = QFont(app.font())
    if not font.family():
        font.setFamily("Segoe UI")
    font.setPointSizeF(max(8.5, 10.0 * _CURRENT_FACTOR))
    app.setFont(font)

    try:
        from ui.styles import get_stylesheet

        app.setStyleSheet(get_stylesheet(_CURRENT_FACTOR))
    except Exception:
        pass
    return _CURRENT_FACTOR


def scale_px(value: int, mode: str | None = None) -> int:
    return max(1, round(value * current_scale_factor(QApplication.instance(), mode)))
