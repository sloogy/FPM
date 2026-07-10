"""Globale UI-Skalierung für FountainPen Manager.

Ziel: Schrift, Eingabefelder, Tabellenzeilen und Dialoge sollen auf kleinen
Laptop-Displays und HiDPI-Umgebungen lesbar bleiben. Die Einstellung wird in
AppSettings unter ``ui_scale_mode`` gespeichert.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Optional
from types import SimpleNamespace

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont


@dataclass(frozen=True)
class ScalePreset:
    key: str
    label: str
    factor: float


PRESETS: list[ScalePreset] = [
    ScalePreset("auto", "Auto – Bildschirm erkennen", 1.0),
    ScalePreset("compact", "Kompakt", 0.92),
    ScalePreset("normal", "Normal", 1.00),
    ScalePreset("laptop", "Laptop groß", 1.18),
    ScalePreset("large", "Sehr groß", 1.34),
]

_SCALE_STATE = SimpleNamespace(factor=1.0, patch_installed=False, original_set_stylesheet=None)


def _scale_inline_css(css: str, factor: float) -> str:
    """Skaliert häufige Inline-QSS-Angaben wie ``font-size:13px``.

    Viele ältere Widgets setzen eigene Stylesheets. Diese würden die globale
    App-Schrift übersteuern. Darum skalieren wir nur offensichtliche px-Werte
    in Layout-/Schrift-Eigenschaften. Farben wie ``#2563eb`` bleiben unberührt.
    """
    if not css or abs(factor - 1.0) < 0.03:
        return css

    props = (
        "font-size", "padding", "margin", "min-height", "max-height",
        "min-width", "max-width", "border-radius", "width", "height",
        "spacing", "left", "right", "top", "bottom"
    )
    prop_pat = "|".join(re.escape(p) for p in props)

    def repl(match: re.Match) -> str:
        prefix = match.group(1)
        num = float(match.group(2))
        value = max(1, int(round(num * factor)))
        return f"{prefix}{value}px"

    return re.sub(rf"((?:{prop_pat})\s*:\s*)(\d+(?:\.\d+)?)px", repl, css)


def install_inline_stylesheet_scaler() -> None:
    """Patcht QWidget.setStyleSheet, damit alte Inline-QSS mit skaliert.

    QApplication.setStyleSheet bleibt unangetastet; das globale Stylesheet ist
    bereits über ``get_stylesheet(scale)`` skaliert.
    """
    if _SCALE_STATE.patch_installed:
        return
    try:
        from PySide6.QtWidgets import QWidget
        _SCALE_STATE.original_set_stylesheet = QWidget.setStyleSheet

        def _patched_set_stylesheet(self, stylesheet: str) -> None:
            return _SCALE_STATE.original_set_stylesheet(self, _scale_inline_css(stylesheet or "", _SCALE_STATE.factor))

        QWidget.setStyleSheet = _patched_set_stylesheet
        _SCALE_STATE.patch_installed = True
    except Exception:
        pass


def preset_factor(mode: str | None) -> float:
    mode = (mode or "auto").strip().lower()
    for preset in PRESETS:
        if preset.key == mode:
            return preset.factor
    return 1.0


def _screen_auto_factor(app: QApplication) -> float:
    screen = app.primaryScreen()
    if screen is None:
        return 1.0

    dpi = float(screen.logicalDotsPerInch() or 96.0)
    dpi_scale = max(1.0, dpi / 96.0)
    size = screen.availableGeometry().size()
    height = size.height()

    # Viele Laptops melden trotz hoher Pixeldichte nur 96 DPI. Dann hilft eine
    # moderate Mindestskalierung bei 900p/1080p-Höhe, ohne Desktop-Monitore zu
    # riesig zu machen.
    if height <= 820:
        size_boost = 1.22
    elif height <= 950:
        size_boost = 1.16
    elif height <= 1120:
        size_boost = 1.08
    else:
        size_boost = 1.0

    return max(1.0, min(1.45, dpi_scale * size_boost))


def current_scale_factor(app: Optional[QApplication] = None, mode: str | None = None) -> float:
    app = app or QApplication.instance()
    if app is None:
        return preset_factor(mode)
    mode = (mode or "auto").strip().lower()
    if mode == "auto":
        return _screen_auto_factor(app)
    return preset_factor(mode)


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


def apply_ui_scaling(app: Optional[QApplication] = None, mode: str | None = None) -> float:
    """Wendet Schrift und Stylesheet global neu an und liefert den Faktor zurück."""
    app = app or QApplication.instance()
    if app is None:
        return 1.0

    if mode is None:
        mode = _load_mode_from_settings("auto")
    factor = current_scale_factor(app, mode)
    _SCALE_STATE.factor = factor
    install_inline_stylesheet_scaler()

    # Point Size skaliert sauber mit Qt/DPI. Das Stylesheet bekommt zusätzlich
    # skalierte Pixelwerte, damit Inline-/StyleSheet-Layouts nicht zu klein
    # bleiben.
    font = QFont("Segoe UI")
    font.setPointSizeF(max(9.0, 10.0 * factor))
    app.setFont(font)

    try:
        from ui.styles import get_stylesheet
        app.setStyleSheet(get_stylesheet(factor))
    except Exception:
        pass
    return factor


def scale_px(value: int, mode: str | None = None) -> int:
    app = QApplication.instance()
    return max(1, int(round(value * current_scale_factor(app, mode))))
