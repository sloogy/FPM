from __future__ import annotations

from pathlib import Path


def test_auto_scaling_does_not_double_apply_qt_dpi():
    source = Path('ui/ui_scale.py').read_text(encoding='utf-8')
    assert 'dpi = float(screen.logicalDotsPerInch()' not in source
    assert 'dpi / 96.0' not in source
    assert 'Qt liefert Geometrien bereits in logischen Pixeln' in source


def test_main_window_geometry_is_screen_bounded():
    source = Path('ui/main_window.py').read_text(encoding='utf-8')
    assert '_apply_responsive_window_geometry' in source
    assert 'available.width() - margin' in source
    assert 'available.height() - margin' in source
    assert 'screenChanged.connect' in source


def test_scale_presets_remain_bounded():
    source = Path('ui/ui_scale.py').read_text(encoding='utf-8')
    assert 'ScalePreset("compact", "Kompakt", 0.90)' in source
    assert 'ScalePreset("normal", "Normal", 1.00)' in source
    assert 'ScalePreset("laptop", "Laptop groß", 1.12)' in source
    assert 'ScalePreset("large", "Sehr groß", 1.28)' in source
