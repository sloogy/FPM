"""Zentrales Stylesheet für FountainPen Manager.

Alle Farben kommen aus dem aktiven Designprofil (``ui/theme_manager.py``).
Bis v1.0.3 standen hier Literale, die ein Profil nur per Textersetzung treffen
konnte - was zwangslaeufig unvollstaendig blieb: weisse Karten und weisse
Schrift auf hellem Grund waren die Folge. Jetzt gibt es keine Farbliterale
mehr in dieser Datei.

Die Groessen skalieren weiterhin ueber einen Faktor; er kommt aus der
Schriftgroesse des Profils.
"""
from __future__ import annotations

from ui import theme
from ui.host_theme import install_inline_theme
from ui.theme_manager import ThemeManager


def _px(value: int | float, scale: float) -> int:
    return max(1, int(round(float(value) * float(scale))))


def get_stylesheet(scale: float = 1.0) -> str:
    """Globales Stylesheet fuer das aktive Profil."""
    # Solange einzelne Widgets ihre Farben noch inline setzen, muessen auch
    # diese durch die Profilzuordnung laufen - sonst schlagen sie das globale
    # Stylesheet und bleiben hell.
    install_inline_theme()
    profile = ThemeManager.instance().current_profile()
    return _build_stylesheet(scale * profile.scale)


def _build_stylesheet(scale: float = 1.0) -> str:
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

    c = theme.color
    # Die Seitenleiste ist eine eigene Flaeche mit eigener Textfarbe: in hellen
    # Profilen dunkel, in dunklen noch dunkler. Ihr Text folgt deshalb
    # "seitenleiste_text" und nicht der allgemeinen Textfarbe.
    side_bg = c("hintergrund_seitenleiste")
    side_panel = theme.sidebar_panel()
    side_text = c("seitenleiste_text")
    side_dim = c("seitenleiste_text_gedimmt")

    return f"""
/* ── Basis ──────────────────────────────────────────────── */
QMainWindow, QDialog, QWidget {{
    background-color: {c("hintergrund_app")};
    color: {c("text")};
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: {base}px;
}}

/* ── Sidebar (einfacher Calibre-Modus) ──────────────────── */
QWidget#simpleSidebar {{
    background-color: {side_bg};
    color: {side_text};
    border-right: 3px solid {c("akzent")};
    min-width: {sidebar_w_hint}px;
}}
QWidget#simpleSidebar QWidget {{
    background-color: {side_panel};
    color: {side_text};
}}
QLabel#sidebarLogo {{
    color: {side_text};
    font-size: {_px(18, scale)}px;
    font-weight: 800;
    padding: {_px(22, scale)}px {_px(18, scale)}px {_px(18, scale)}px {_px(18, scale)}px;
    background-color: {theme.shade(side_bg, 0.8)};
    border-bottom: 1px solid {theme.shade(side_bg, 2.0)};
}}
QPushButton#navButton {{
    background-color: {side_panel};
    color: {side_text};
    border: none;
    text-align: left;
    padding: {_px(13, scale)}px {_px(18, scale)}px;
    font-size: {nav}px;
    border-radius: 0;
    min-height: {_px(42, scale)}px;
}}
QPushButton#navButton:hover {{ background-color: {theme.sidebar_panel_hover()}; color: {side_text}; }}
QPushButton#navButton:checked {{ background-color: {c("seitenleiste_aktiv")}; color: {c("akzent_text")}; font-weight: 800; }}
QPushButton#modeToggleButton {{
    background-color: {c("akzent")};
    color: {c("akzent_text")};
    border: 1px solid {theme.shade(c("akzent"), 1.3)};
    border-radius: {_px(8, scale)}px;
    padding: {_px(9, scale)}px {_px(12, scale)}px;
    margin: {_px(8, scale)}px {_px(12, scale)}px {_px(4, scale)}px {_px(12, scale)}px;
    font-weight: 800;
}}
QPushButton#modeToggleButton:hover {{ background-color: {theme.hover("akzent")}; }}
QLabel#sidebarHint {{ color: {side_dim}; font-size: {tiny}px; padding: {_px(10, scale)}px {_px(14, scale)}px; background-color: {side_panel}; }}

QLabel#sidebarGroupLabel {{
    color: {side_dim};
    font-size: {tiny}px;
    font-weight: 700;
    letter-spacing: {_px(1, scale)}px;
    padding: {_px(12, scale)}px {_px(12, scale)}px {_px(4, scale)}px {_px(14, scale)}px;
    background-color: {side_bg};
}}

QLabel#sidebarVersion {{ color: {side_dim}; font-size: {tiny}px; padding: {_px(10, scale)}px; background-color: {side_panel}; }}

/* ── Toolbar ─────────────────────────────────────────────── */
QToolBar#mainToolbar {{
    background: {c("hintergrund_panel")};
    border-bottom: 1px solid {c("rand")};
    spacing: {_px(6, scale)}px;
    padding: {_px(5, scale)}px {_px(8, scale)}px;
}}
QToolBar#mainToolbar QToolButton {{
    background: {c("tabelle_alt")};
    border: 1px solid {c("rand")};
    border-radius: {radius}px;
    padding: {_px(7, scale)}px {_px(12, scale)}px;
    min-height: {btn_h}px;
    font-size: {small}px;
    color: {c("text")};
}}
QToolBar#mainToolbar QToolButton:hover {{ background: {c("hover_hintergrund")}; color: {c("hover_text")}; border-color: {c("akzent")}; }}
QToolBar#mainToolbar QToolButton:pressed {{ background: {c("auswahl_hintergrund")}; color: {c("auswahl_text")}; }}

QPushButton#dashboardPrimaryAction {{
    background-color: {c("akzent")};
    color: {c("akzent_text")};
    border: none;
    border-radius: {radius}px;
    padding: {_px(10, scale)}px {_px(16, scale)}px;
    min-height: {_px(42, scale)}px;
    font-weight: 800;
}}
QPushButton#dashboardPrimaryAction:hover {{ background-color: {theme.hover("akzent")}; }}
QPushButton#dashboardPrimaryAction:pressed {{ background-color: {theme.pressed("akzent")}; }}

/* ── Buttons ─────────────────────────────────────────────── */
/* Farben ja, Groessen nein: Ein zusaetzliches Padding auf ALLEN Knoepfen
   sprengte schmale Werkzeugleisten, deren Beschriftung dann abgeschnitten
   wurde. Die Groesse bleibt deshalb wie gehabt bei Qt. */
QPushButton {{
    min-height: {btn_h}px;
    font-size: {base}px;
    background-color: {c("hintergrund_panel")};
    color: {c("text")};
    border: 1px solid {c("rand")};
    border-radius: {radius}px;
}}
QPushButton:hover {{ background-color: {c("hover_hintergrund")}; color: {c("hover_text")}; }}
QPushButton:disabled {{ color: {c("text_gedimmt")}; border-color: {c("rand")}; }}
QPushButton.primary, QPushButton.success, QPushButton.danger, QPushButton.warning, QPushButton.secondary {{
    border: none;
    padding: {_px(8, scale)}px {_px(18, scale)}px;
    border-radius: {radius}px;
    font-weight: bold;
}}
QPushButton.primary {{ background-color: {c("akzent")}; color: {c("akzent_text")}; }}
QPushButton.primary:hover   {{ background-color: {theme.hover("akzent")}; }}
QPushButton.primary:pressed {{ background-color: {theme.pressed("akzent")}; }}
QPushButton.success {{ background-color: {c("erfolg")}; color: {c("erfolg_text")}; }}
QPushButton.success:hover {{ background-color: {theme.hover("erfolg")}; }}
QPushButton.danger {{ background-color: {c("gefahr")}; color: {c("gefahr_text")}; }}
QPushButton.danger:hover {{ background-color: {theme.hover("gefahr")}; }}
QPushButton.warning {{ background-color: {c("warnung")}; color: {c("warnung_text")}; }}
QPushButton.warning:hover {{ background-color: {theme.hover("warnung")}; }}
QPushButton.secondary {{ background-color: {c("gedaempft")}; color: {c("gedaempft_text")}; }}
QPushButton.secondary:hover {{ background-color: {theme.hover("gedaempft")}; }}

/* ── Eingabefelder ───────────────────────────────────────── */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {{
    background-color: {c("eingabe_hintergrund")};
    color: {c("text")};
    border: 1px solid {c("rand")};
    border-radius: {radius}px;
    padding: {pad_y}px {pad_x}px;
    font-size: {base}px;
    min-height: {input_h}px;
    selection-background-color: {c("auswahl_hintergrund")};
    selection-color: {c("auswahl_text")};
}}
QTextEdit, QPlainTextEdit {{
    background-color: {c("eingabe_hintergrund")};
    color: {c("text")};
    border: 1px solid {c("rand")};
    border-radius: {radius}px;
    padding: {pad_y}px {pad_x}px;
    font-size: {base}px;
    min-height: {_px(58, scale)}px;
    selection-background-color: {c("auswahl_hintergrund")};
    selection-color: {c("auswahl_text")};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {{
    border: 2px solid {c("akzent")};
    padding: {_px(5, scale)}px {_px(8, scale)}px;
}}
QTextEdit:focus {{ border: 2px solid {c("akzent")}; }}
QComboBox::drop-down {{ border: none; width: {_px(24, scale)}px; }}
QComboBox::down-arrow {{ image: none; }}
QComboBox QAbstractItemView {{
    background-color: {c("hintergrund_panel")};
    color: {c("text")};
    selection-background-color: {c("auswahl_hintergrund")};
    selection-color: {c("auswahl_text")};
    border: 1px solid {c("rand")};
}}

/* ── Tabellen ────────────────────────────────────────────── */
QTableWidget, QTableView {{
    background-color: {c("tabelle_hintergrund")};
    color: {c("text")};
    border: 1px solid {c("rand")};
    border-radius: {radius}px;
    gridline-color: {c("tabelle_gitter")};
    alternate-background-color: {c("tabelle_alt")};
    selection-background-color: {c("auswahl_hintergrund")};
    selection-color: {c("auswahl_text")};
    font-size: {small}px;
}}
QHeaderView::section {{
    background-color: {c("tabelle_header")};
    color: {c("tabelle_header_text")};
    padding: {_px(8, scale)}px {_px(10, scale)}px;
    border: none;
    border-right: 1px solid {c("tabelle_gitter")};
    border-bottom: 1px solid {c("tabelle_gitter")};
    font-weight: bold;
    font-size: {small}px;
    min-height: {_px(32, scale)}px;
}}
QTableWidget::item {{ padding: {_px(6, scale)}px {_px(8, scale)}px; min-height: {row_h}px; }}
QTableWidget::item:selected {{ background-color: {c("auswahl_hintergrund")}; color: {c("auswahl_text")}; }}

/* ── GroupBox ────────────────────────────────────────────── */
QGroupBox {{
    background-color: {c("karte_hintergrund")};
    color: {c("text")};
    border: 1px solid {c("karte_rand")};
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
    color: {c("text_gedimmt")};
    background-color: {c("hintergrund_app")};
    font-size: {small}px;
}}

/* ── Scrollbar ───────────────────────────────────────────── */
QScrollBar:vertical {{ border: none; background: {c("tabelle_alt")}; width: {_px(10, scale)}px; border-radius: {_px(5, scale)}px; }}
QScrollBar::handle:vertical {{ background: {c("rand")}; border-radius: {_px(5, scale)}px; }}
QScrollBar::handle:vertical:hover {{ background: {c("text_gedimmt")}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollArea {{ background: transparent; border: none; }}

/* ── Labels ─────────────────────────────────────────────── */
QLabel {{ background: transparent; }}
QLabel#page_title {{ font-size: {title}px; font-weight: bold; color: {c("text")}; }}
QLabel#stat_value {{ font-size: {stat}px; font-weight: bold; color: {c("text")}; }}
QLabel#stat_label {{ font-size: {tiny}px; color: {c("text_gedimmt")}; text-transform: uppercase; }}

QLabel[secondaryText="true"] {{
    color: {c("text_gedimmt")};
}}

/* ── Splitter ────────────────────────────────────────────── */
QSplitter::handle {{ background-color: {c("rand")}; }}
QSplitter::handle:horizontal {{ width: 1px; }}

/* ── Ausgaben-Tracker Summary / Details ─────────────────── */
QWidget#summaryCard {{ background: {c("karte_hintergrund")}; border: 1px solid {c("karte_rand")}; border-radius: {_px(8, scale)}px; }}
QLabel#summaryValue {{ font-size: {_px(17, scale)}px; font-weight: 800; color: {c("text")}; border: none; }}
QLabel#summaryLabel {{ font-size: {_px(10, scale)}px; color: {c("text_gedimmt")}; border: none; }}
QWidget#detailPanel {{ background: {c("hintergrund_panel")}; border-left: 1px solid {c("rand")}; }}

/* ── Tooltip ─────────────────────────────────────────────── */
QToolTip {{ background-color: {side_bg}; color: {side_text}; border: 1px solid {c("rand")}; padding: {_px(6, scale)}px {_px(10, scale)}px; border-radius: {_px(4, scale)}px; font-size: {small}px; }}

/* ── CheckBox ────────────────────────────────────────────── */
QCheckBox::indicator {{ width: {_px(18, scale)}px; height: {_px(18, scale)}px; border: 2px solid {c("rand")}; border-radius: {_px(3, scale)}px; background: {c("eingabe_hintergrund")}; }}
QCheckBox::indicator:checked {{ background-color: {c("akzent")}; border-color: {c("akzent")}; }}
QCheckBox {{ font-size: {base}px; spacing: {_px(8, scale)}px; min-height: {_px(26, scale)}px; }}
QRadioButton {{ font-size: {base}px; spacing: {_px(8, scale)}px; min-height: {_px(26, scale)}px; }}

/* ── FormLabel ───────────────────────────────────────────── */
QFormLayout QLabel {{ font-size: {small}px; color: {c("text")}; min-height: {_px(24, scale)}px; }}

/* ── Tabs/List ───────────────────────────────────────────── */
QTabWidget::pane {{ border: 1px solid {c("rand")}; background: {c("hintergrund_panel")}; }}
QTabBar::tab {{ padding: {_px(9, scale)}px {_px(16, scale)}px; font-size: {base}px; min-height: {_px(28, scale)}px;
    background: {c("tabelle_alt")}; color: {c("text_gedimmt")}; border: 1px solid {c("rand")}; }}
QTabBar::tab:selected {{ background: {c("hintergrund_panel")}; color: {c("text")}; font-weight: bold; }}
QListWidget {{ background-color: {c("hintergrund_panel")}; color: {c("text")}; border: 1px solid {c("rand")}; }}
QListWidget::item {{ min-height: {_px(30, scale)}px; font-size: {base}px; }}
QListWidget::item:selected {{ background-color: {c("auswahl_hintergrund")}; color: {c("auswahl_text")}; }}

/* ── Menue ──────────────────────────────────────────────── */
QMenu {{ background-color: {c("hintergrund_panel")}; color: {c("text")}; border: 1px solid {c("rand")}; }}
QMenu::item:selected {{ background-color: {c("auswahl_hintergrund")}; color: {c("auswahl_text")}; }}
QMenuBar {{ background-color: {c("hintergrund_panel")}; color: {c("text")}; }}
QMenuBar::item:selected {{ background-color: {c("hover_hintergrund")}; color: {c("hover_text")}; }}

/* ── Dialog ─────────────────────────────────────────────── */
QDialog {{ background-color: {c("hintergrund_app")}; color: {c("text")}; }}
"""
