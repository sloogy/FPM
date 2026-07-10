"""Zentrales Stylesheet für FountainPen Manager.

v0.2.36:
- Globale UI-Skalierung: Schrift, Eingabefelder, Tabellen, Sidebar und
  Dialogelemente werden über einen Faktor skaliert.
- Eingabefelder bekommen Mindesthöhen, damit Text auf Laptop-/HiDPI-Displays
  nicht mehr abgeschnitten wirkt.
"""
from __future__ import annotations


def _px(value: int | float, scale: float) -> int:
    return max(1, int(round(float(value) * float(scale))))


def get_stylesheet(scale: float = 1.0) -> str:
    scale = max(0.85, min(1.50, float(scale or 1.0)))
    base = _px(14, scale)
    small = _px(13, scale)
    tiny = _px(12, scale)
    nav = _px(16, scale)
    title = _px(22, scale)
    stat = _px(28, scale)
    input_h = _px(30, scale)
    btn_h = _px(32, scale)
    row_h = _px(30, scale)
    pad_y = _px(6, scale)
    pad_x = _px(9, scale)
    card_pad_top = _px(18, scale)
    radius = _px(6, scale)
    sidebar_w_hint = _px(240, scale)

    return f"""
/* ── Basis ──────────────────────────────────────────────── */
QMainWindow, QDialog, QWidget {{
    background-color: #f0f3f7;
    color: #2c3e50;
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: {base}px;
}}

/* ── Sidebar (einfacher Calibre-Modus) ──────────────────── */
QWidget#simpleSidebar {{
    background-color: #0b1220;
    color: #ffffff;
    border-right: 3px solid #2563eb;
    min-width: {sidebar_w_hint}px;
}}
QWidget#simpleSidebar QWidget {{
    background-color: #18212d;
    color: #e5edf5;
}}
QLabel#sidebarLogo {{
    color: #f8fafc;
    font-size: {_px(18, scale)}px;
    font-weight: 800;
    padding: {_px(22, scale)}px {_px(18, scale)}px {_px(18, scale)}px {_px(18, scale)}px;
    background-color: #020617;
    border-bottom: 1px solid #334155;
}}
QPushButton#navButton {{
    background-color: #111827;
    color: #ffffff;
    border: none;
    text-align: left;
    padding: {_px(13, scale)}px {_px(18, scale)}px;
    font-size: {nav}px;
    border-radius: 0;
    min-height: {_px(42, scale)}px;
}}
QPushButton#navButton:hover {{ background-color: #1f2937; color: #ffffff; }}
QPushButton#navButton:checked {{ background-color: #1d4ed8; color: #ffffff; font-weight: 800; }}
QPushButton#modeToggleButton {{
    background-color: #2563eb;
    color: #ffffff;
    border: 1px solid #60a5fa;
    border-radius: {_px(8, scale)}px;
    padding: {_px(9, scale)}px {_px(12, scale)}px;
    margin: {_px(8, scale)}px {_px(12, scale)}px {_px(4, scale)}px {_px(12, scale)}px;
    font-weight: 800;
}}
QPushButton#modeToggleButton:hover {{ background-color: #1d4ed8; }}
QLabel#sidebarHint {{ color: #94a3b8; font-size: {tiny}px; padding: {_px(10, scale)}px {_px(14, scale)}px; background-color: #18212d; }}

QLabel#sidebarGroupLabel {{
    color: #7f8c8d;
    font-size: {tiny}px;
    font-weight: 700;
    letter-spacing: {_px(1, scale)}px;
    padding: {_px(12, scale)}px {_px(12, scale)}px {_px(4, scale)}px {_px(14, scale)}px;
    background-color: #0b1220;
}}

QLabel#sidebarVersion {{ color: #94a3b8; font-size: {tiny}px; padding: {_px(10, scale)}px; background-color: #18212d; }}

/* ── Toolbar ─────────────────────────────────────────────── */
QToolBar#mainToolbar {{
    background: #ffffff;
    border-bottom: 1px solid #d5dce6;
    spacing: {_px(6, scale)}px;
    padding: {_px(5, scale)}px {_px(8, scale)}px;
}}
QToolBar#mainToolbar QToolButton {{
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: {radius}px;
    padding: {_px(7, scale)}px {_px(12, scale)}px;
    min-height: {btn_h}px;
    font-size: {small}px;
    color: #2c3e50;
}}
QToolBar#mainToolbar QToolButton:hover {{ background: #e8f1ff; border-color: #3498db; }}
QToolBar#mainToolbar QToolButton:pressed {{ background: #d6e9f8; }}

QPushButton#dashboardPrimaryAction {{
    background-color: #2563eb;
    color: white;
    border: none;
    border-radius: {radius}px;
    padding: {_px(10, scale)}px {_px(16, scale)}px;
    min-height: {_px(42, scale)}px;
    font-weight: 800;
}}
QPushButton#dashboardPrimaryAction:hover {{ background-color: #1d4ed8; }}
QPushButton#dashboardPrimaryAction:pressed {{ background-color: #1e40af; }}

/* ── Buttons ─────────────────────────────────────────────── */
QPushButton {{
    min-height: {btn_h}px;
    font-size: {base}px;
}}
QPushButton.primary, QPushButton.success, QPushButton.danger, QPushButton.warning, QPushButton.secondary {{
    color: white;
    border: none;
    padding: {_px(8, scale)}px {_px(18, scale)}px;
    border-radius: {radius}px;
    font-weight: bold;
}}
QPushButton.primary {{ background-color: #3498db; }}
QPushButton.primary:hover   {{ background-color: #2980b9; }}
QPushButton.primary:pressed {{ background-color: #1f6391; }}
QPushButton.success {{ background-color: #27ae60; }}
QPushButton.success:hover {{ background-color: #219a52; }}
QPushButton.danger {{ background-color: #e74c3c; }}
QPushButton.danger:hover {{ background-color: #c0392b; }}
QPushButton.warning {{ background-color: #f39c12; }}
QPushButton.warning:hover {{ background-color: #d68910; }}
QPushButton.secondary {{ background-color: #7f8c8d; }}
QPushButton.secondary:hover {{ background-color: #6c7a7d; }}

/* ── Eingabefelder ───────────────────────────────────────── */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {{
    background-color: white;
    border: 1px solid #d5dce6;
    border-radius: {radius}px;
    padding: {pad_y}px {pad_x}px;
    font-size: {base}px;
    min-height: {input_h}px;
    selection-background-color: #3498db;
}}
QTextEdit, QPlainTextEdit {{
    background-color: white;
    border: 1px solid #d5dce6;
    border-radius: {radius}px;
    padding: {pad_y}px {pad_x}px;
    font-size: {base}px;
    min-height: {_px(58, scale)}px;
    selection-background-color: #3498db;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {{
    border: 2px solid #3498db;
    padding: {_px(5, scale)}px {_px(8, scale)}px;
}}
QTextEdit:focus {{ border: 2px solid #3498db; }}
QComboBox::drop-down {{ border: none; width: {_px(24, scale)}px; }}
QComboBox::down-arrow {{ image: none; }}

/* ── Tabellen ────────────────────────────────────────────── */
QTableWidget {{
    background-color: white;
    border: 1px solid #d5dce6;
    border-radius: {radius}px;
    gridline-color: #edf0f5;
    alternate-background-color: #f7f9fc;
    selection-background-color: #d6e9f8;
    selection-color: #2c3e50;
    font-size: {small}px;
}}
QHeaderView::section {{
    background-color: #edf1f7;
    color: #4a5568;
    padding: {_px(8, scale)}px {_px(10, scale)}px;
    border: none;
    border-right: 1px solid #d5dce6;
    border-bottom: 1px solid #d5dce6;
    font-weight: bold;
    font-size: {small}px;
    min-height: {_px(32, scale)}px;
}}
QTableWidget::item {{ padding: {_px(6, scale)}px {_px(8, scale)}px; min-height: {row_h}px; }}
QTableWidget::item:selected {{ background-color: #3498db; color: white; }}

/* ── GroupBox ────────────────────────────────────────────── */
QGroupBox {{
    background-color: white;
    border: 1px solid #d5dce6;
    border-radius: {_px(7, scale)}px;
    margin-top: {_px(12, scale)}px;
    padding: {card_pad_top}px {_px(12, scale)}px {_px(12, scale)}px {_px(12, scale)}px;
    font-weight: bold;
    font-size: {base}px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: {_px(12, scale)}px;
    padding: 0 {_px(6, scale)}px;
    color: #4a5568;
    font-size: {small}px;
}}

/* ── Scrollbar ───────────────────────────────────────────── */
QScrollBar:vertical {{ border: none; background: #edf0f5; width: {_px(10, scale)}px; border-radius: {_px(5, scale)}px; }}
QScrollBar::handle:vertical {{ background: #bdc3c7; border-radius: {_px(5, scale)}px; }}
QScrollBar::handle:vertical:hover {{ background: #95a5a6; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

/* ── Labels ─────────────────────────────────────────────── */
QLabel#page_title {{ font-size: {title}px; font-weight: bold; color: #1e2a38; }}
QLabel#stat_value {{ font-size: {stat}px; font-weight: bold; color: #2c3e50; }}
QLabel#stat_label {{ font-size: {tiny}px; color: #7f8c8d; text-transform: uppercase; }}

/* ── Splitter ────────────────────────────────────────────── */
QSplitter::handle {{ background-color: #d5dce6; }}
QSplitter::handle:horizontal {{ width: 1px; }}

/* ── Ausgaben-Tracker Summary / Details ─────────────────── */
QWidget#summaryCard {{ background: #ffffff; border: 1px solid #d5dce6; border-radius: {_px(8, scale)}px; }}
QLabel#summaryValue {{ font-size: {_px(17, scale)}px; font-weight: 800; color: #1e2a38; border: none; }}
QLabel#summaryLabel {{ font-size: {_px(10, scale)}px; color: #64748b; border: none; }}
QWidget#detailPanel {{ background: #ffffff; border-left: 1px solid #d5dce6; }}

/* ── Tooltip ─────────────────────────────────────────────── */
QToolTip {{ background-color: #2c3e50; color: white; border: none; padding: {_px(6, scale)}px {_px(10, scale)}px; border-radius: {_px(4, scale)}px; font-size: {small}px; }}

/* ── CheckBox ────────────────────────────────────────────── */
QCheckBox::indicator {{ width: {_px(18, scale)}px; height: {_px(18, scale)}px; border: 2px solid #bdc3c7; border-radius: {_px(3, scale)}px; background: white; }}
QCheckBox::indicator:checked {{ background-color: #3498db; border-color: #3498db; }}
QCheckBox {{ font-size: {base}px; spacing: {_px(8, scale)}px; min-height: {_px(26, scale)}px; }}
QRadioButton {{ font-size: {base}px; spacing: {_px(8, scale)}px; min-height: {_px(26, scale)}px; }}

/* ── FormLabel ───────────────────────────────────────────── */
QFormLayout QLabel {{ font-size: {small}px; color: #4a5568; min-height: {_px(24, scale)}px; }}

/* ── Tabs/List ───────────────────────────────────────────── */
QTabBar::tab {{ padding: {_px(9, scale)}px {_px(16, scale)}px; font-size: {base}px; min-height: {_px(28, scale)}px; }}
QListWidget::item {{ min-height: {_px(30, scale)}px; font-size: {base}px; }}

/* ── Dialog ─────────────────────────────────────────────── */
QDialog {{ background-color: #f0f3f7; }}
"""
