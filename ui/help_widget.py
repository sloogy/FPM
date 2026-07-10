"""Zentrale Hilfe für Regeln, Auto Mode, Service und erste Schritte."""
from __future__ import annotations
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTabWidget, QScrollArea, QFrame, QGroupBox, QGridLayout, QHBoxLayout, QPushButton
from i18n.translator import t
from i18n.qt_i18n import translate_source_text

def _scroll_page() -> tuple[QWidget, QVBoxLayout]:
    page = QWidget()
    outer = QVBoxLayout(page)
    outer.setContentsMargins(0, 0, 0, 0)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameStyle(QFrame.Shape.NoFrame)
    body = QWidget()
    layout = QVBoxLayout(body)
    layout.setContentsMargins(18, 18, 18, 18)
    layout.setSpacing(12)
    scroll.setWidget(body)
    outer.addWidget(scroll)
    return (page, layout)

def _card(title: str, body: str) -> QGroupBox:
    grp = QGroupBox(translate_source_text(title))
    lay = QVBoxLayout(grp)
    txt = QLabel(translate_source_text(body))
    txt.setWordWrap(True)
    txt.setTextFormat(Qt.TextFormat.RichText)
    txt.setStyleSheet('border:none; color:#2c3e50; line-height:1.25;')
    lay.addWidget(txt)
    return grp

class HelpWidget(QWidget):
    """Erklärbare Hilfe direkt in der App, ohne externe Dokumentation."""
    tour_requested = Signal()

    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(14)
        title = QLabel(t('ui.help_widget.hilfe_regel_erklarungen_0fd89964'))
        title.setObjectName('page_title')
        root.addWidget(title)
        hint = QLabel(t('ui.help_widget.diese_hilfe_erklart_die_wichtigsten_entscheidung_3ce2e6c9'))
        hint.setWordWrap(True)
        hint.setStyleSheet('color:#7f8c8d; padding:4px;')
        root.addWidget(hint)
        tour_card = QFrame()
        tour_card.setStyleSheet('QFrame { background:#ecf6fd; border:1px solid #aed4ee; border-radius:8px; }')
        tcl = QHBoxLayout(tour_card)
        tcl.setContentsMargins(16, 12, 16, 12)
        tour_text = QLabel(t('tour.triggers.help_text'))
        tour_text.setWordWrap(True)
        tour_text.setStyleSheet('border:none; background:transparent; color:#2c3e50;')
        tcl.addWidget(tour_text, 1)
        tour_btn = QPushButton(t('tour.triggers.start_button'))
        tour_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        tour_btn.setStyleSheet('background:#3498db; color:white; border:none; padding:8px 18px; border-radius:5px; font-weight:bold;')
        tour_btn.clicked.connect(self.tour_requested)
        tcl.addWidget(tour_btn)
        root.addWidget(tour_card)
        tabs = QTabWidget()
        root.addWidget(tabs, 1)
        self._add_start_tab(tabs)
        self._add_rotation_tab(tabs)
        self._add_rules_tab(tabs)
        self._add_auto_tab(tabs)
        self._add_service_tab(tabs)
        self._add_consumption_tab(tabs)
        self._add_research_tab(tabs)
        self._add_glossary_tab(tabs)

    def _add_start_tab(self, tabs: QTabWidget):
        page, lay = _scroll_page()
        lay.addWidget(_card(t('help.quickstart_title'), t('help.quickstart_body')))
        lay.addWidget(_card(t('help.manual_title'), t('help.manual_body')))
        lay.addWidget(_card(t('help.dashboard_title'), t('help.dashboard_body')))
        lay.addWidget(_card(t('help.mode_title'), t('help.mode_body')))
        lay.addStretch()
        tabs.addTab(page, t('help.start_tab'))

    def _add_rotation_tab(self, tabs: QTabWidget):
        """v0.2.81: Der Kern-Workflow der App war in der Hilfe nicht erklärt."""
        page, lay = _scroll_page()
        lay.addWidget(_card(t('help.rotation.workflow_title'), t('help.rotation.workflow_body')))
        lay.addWidget(_card(t('help.rotation.score_title'), t('help.rotation.score_body')))
        lay.addWidget(_card(t('help.rotation.reroll_title'), t('help.rotation.reroll_body')))
        lay.addWidget(_card(t('help.rotation.random_title'), t('help.rotation.random_body')))
        lay.addWidget(_card(t('help.rotation.pins_title'), t('help.rotation.pins_body')))
        lay.addStretch()
        tabs.addTab(page, t('help.rotation.tab'))

    def _add_research_tab(self, tabs: QTabWidget):
        """v0.2.81: Hersteller-zuerst-Recherche und Overlay dokumentieren."""
        page, lay = _scroll_page()
        lay.addWidget(_card(t('help.research.lookup_title'), t('help.research.lookup_body')))
        lay.addWidget(_card(t('help.research.sources_title'), t('help.research.sources_body')))
        lay.addWidget(_card(t('help.research.overlay_title'), t('help.research.overlay_body')))
        lay.addStretch()
        tabs.addTab(page, t('help.research.tab'))

    def _add_rules_tab(self, tabs: QTabWidget):
        page, lay = _scroll_page()
        lay.addWidget(_card(t('ui.help_widget.legacy_exact.text_001'), t('ui.help_widget.legacy_exact.text_002')))
        lay.addWidget(_card(t('ui.help_widget.legacy_exact.text_003'), t('ui.help_widget.legacy_exact.text_004')))
        lay.addWidget(_card(t('ui.help_widget.legacy_exact.text_005'), t('ui.help_widget.legacy_exact.text_006')))
        lay.addStretch()
        tabs.addTab(page, t('ui.help_widget.regeln_ac603d2a'))

    def _add_auto_tab(self, tabs: QTabWidget):
        page, lay = _scroll_page()
        lay.addWidget(_card(t('ui.help_widget.full_auto_mode_title'), t('ui.help_widget.legacy_exact.text_007')))
        lay.addWidget(_card(t('ui.help_widget.legacy_exact.text_008'), t('ui.help_widget.legacy_exact.text_009')))
        lay.addStretch()
        tabs.addTab(page, t('ui.help_widget.full_auto_6ff817b9'))

    def _add_service_tab(self, tabs: QTabWidget):
        page, lay = _scroll_page()
        lay.addWidget(_card(t('ui.help_widget.legacy_exact.text_010'), t('ui.help_widget.legacy_exact.text_011')))
        lay.addWidget(_card(t('ui.help_widget.legacy_exact.text_012'), t('ui.help_widget.legacy_exact.text_013')))
        lay.addWidget(_card(t('dashboard.status_labels.dry_risk'), t('ui.help_widget.legacy_exact.text_015')))
        lay.addStretch()
        tabs.addTab(page, t('ui.help_widget.service_92844dc6'))

    def _add_consumption_tab(self, tabs: QTabWidget):
        page, lay = _scroll_page()
        lay.addWidget(_card(t('rules.groups.consumption'), t('ui.help_widget.legacy_exact.text_017')))
        lay.addWidget(_card(t('ui.help_widget.legacy_exact.text_018'), t('ui.help_widget.legacy_exact.text_019')))
        lay.addStretch()
        tabs.addTab(page, t('ui.help_widget.verbrauch_934c21a7'))

    def _add_glossary_tab(self, tabs: QTabWidget):
        page, lay = _scroll_page()
        grid = QGridLayout()
        grid.setColumnStretch(1, 1)
        terms = [('Sheen', t('ui.help_widget.glossary_sheen_desc')), ('Shimmer', t('ui.help_widget.glossary_shimmer_desc')), ('Feathering', t('ui.help_widget.glossary_feathering_desc')), ('Grail', t('ui.help_widget.glossary_grail_desc')), ('Override', t('ui.help_widget.glossary_override_desc')), ('Safety Timer', t('ui.help_widget.glossary_safety_desc')), ('EDC', t('ui.help_widget.glossary_edc_desc')), ('Vac / Vacuum', t('ui.help_widget.glossary_vac_desc')), ('💍 ' + t('ui.help_widget.glossary_fixed_term'), t('ui.help_widget.glossary_fixed_desc')), ('⭐ ' + t('ui.help_widget.glossary_must_term'), t('ui.help_widget.glossary_must_desc')), (t('ui.help_widget.glossary_hard_soft_term'), t('ui.help_widget.glossary_hard_soft_desc')), ('Reroll', t('ui.help_widget.glossary_reroll_desc'))]
        for r, (term, desc) in enumerate(terms):
            a = QLabel(f'<b>{term}</b>')
            b = QLabel(desc)
            b.setWordWrap(True)
            grid.addWidget(a, r, 0)
            grid.addWidget(b, r, 1)
        box = QGroupBox(t('ui.help_widget.glossar_3625192c'))
        box.setLayout(grid)
        lay.addWidget(box)
        lay.addStretch()
        tabs.addTab(page, t('ui.help_widget.glossar_3625192c'))
