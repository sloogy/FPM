"""Durchsuchbare In-App-Hilfe mit direktem Zugriff auf das Handbuch."""
from __future__ import annotations

import re
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from i18n.translator import Translator, t


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
    return page, layout


def _plain_text(text: str) -> str:
    """Macht Rich-Text robust für die Wiki-Suche durchsuchbar."""
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip().casefold()


def _card(title: str, body: str) -> QGroupBox:
    """Erzeugt eine kompakte, durchsuchbare Wiki-Karte."""
    group = QGroupBox(title)
    group.setProperty("help_search_text", _plain_text(f"{title} {body}"))
    layout = QVBoxLayout(group)
    text = QLabel(body)
    text.setWordWrap(True)
    text.setTextFormat(Qt.TextFormat.RichText)
    text.setOpenExternalLinks(True)
    text.setStyleSheet("border:none; color:#2c3e50; line-height:1.25;")
    layout.addWidget(text)
    return group


class HelpWidget(QWidget):
    """Erklärbare Hilfe direkt in der App, inklusive Suche und Handbuch-Link."""

    tour_requested = Signal()

    TOPICS = {
        "start": 0,
        "data_entry": 1,
        "rotation": 2,
        "rules": 3,
        "auto": 4,
        "service": 5,
        "consumption": 6,
        "research": 7,
        "glossary": 8,
    }

    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(14)

        title = QLabel(t("ui.help_widget.hilfe_regel_erklarungen_0fd89964"))
        title.setObjectName("page_title")
        root.addWidget(title)

        hint = QLabel(
            t("ui.help_widget.diese_hilfe_erklart_die_wichtigsten_entscheidung_3ce2e6c9")
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#5f6f72; padding:4px;")
        root.addWidget(hint)

        tools = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setPlaceholderText(t("help.search_placeholder"))
        self.search_edit.setToolTip(t("help.search_tooltip"))
        self.search_edit.setAccessibleName(t("help.search_placeholder"))
        self.search_edit.textChanged.connect(self._filter_help)
        tools.addWidget(self.search_edit, 1)

        manual_button = QPushButton(t("help.open_manual_button"))
        manual_button.setCursor(Qt.CursorShape.PointingHandCursor)
        manual_button.setToolTip(t("help.open_manual_tooltip"))
        manual_button.clicked.connect(self._open_manual)
        tools.addWidget(manual_button)
        root.addLayout(tools)

        self.search_status = QLabel("")
        self.search_status.setWordWrap(True)
        self.search_status.setStyleSheet("color:#5f6f72; padding:0 4px;")
        self.search_status.hide()
        root.addWidget(self.search_status)

        tour_card = QFrame()
        tour_card.setStyleSheet(
            "QFrame { background:#ecf6fd; border:1px solid #aed4ee; border-radius:8px; }"
        )
        tour_layout = QHBoxLayout(tour_card)
        tour_layout.setContentsMargins(16, 12, 16, 12)
        tour_text = QLabel(t("tour.triggers.help_text"))
        tour_text.setWordWrap(True)
        tour_text.setStyleSheet(
            "border:none; background:transparent; color:#2c3e50;"
        )
        tour_layout.addWidget(tour_text, 1)
        tour_button = QPushButton(t("tour.triggers.start_button"))
        tour_button.setCursor(Qt.CursorShape.PointingHandCursor)
        tour_button.setStyleSheet(
            "background:#3498db; color:white; border:none; padding:8px 18px; "
            "border-radius:5px; font-weight:bold;"
        )
        tour_button.clicked.connect(self.tour_requested)
        tour_layout.addWidget(tour_button)
        root.addWidget(tour_card)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)
        self._add_start_tab()
        self._add_data_entry_tab()
        self._add_rotation_tab()
        self._add_rules_tab()
        self._add_auto_tab()
        self._add_service_tab()
        self._add_consumption_tab()
        self._add_research_tab()
        self._add_glossary_tab()

    def show_topic(self, topic: str) -> None:
        """Öffnet ein Hilfethema, z. B. über die kontextbezogene Toolbar-Hilfe."""
        index = self.TOPICS.get(topic, 0)
        self.search_edit.clear()
        if 0 <= index < self.tabs.count():
            self.tabs.setCurrentIndex(index)

    def _filter_help(self, query: str) -> None:
        normalized = _plain_text(query)
        tokens = [token for token in normalized.split(" ") if token]
        total_matches = 0
        first_matching_tab: int | None = None

        for tab_index in range(self.tabs.count()):
            page = self.tabs.widget(tab_index)
            cards = page.findChildren(QGroupBox)
            tab_matches = 0
            for card in cards:
                haystack = str(card.property("help_search_text") or "")
                matches = not tokens or all(token in haystack for token in tokens)
                card.setVisible(matches)
                if matches:
                    tab_matches += 1
            visible = not normalized or tab_matches > 0
            self.tabs.setTabVisible(tab_index, visible)
            if normalized and tab_matches and first_matching_tab is None:
                first_matching_tab = tab_index
            total_matches += tab_matches

        if normalized:
            self.search_status.setText(
                t("help.search_results", count=total_matches)
                if total_matches
                else t("help.search_no_results")
            )
            self.search_status.show()
            if first_matching_tab is not None:
                self.tabs.setCurrentIndex(first_matching_tab)
        else:
            self.search_status.clear()
            self.search_status.hide()

    @staticmethod
    def _manual_candidates() -> list[Path]:
        language = Translator.instance().language
        filename = {
            "de": "BENUTZERHANDBUCH_DE.md",
            "en": "USER_MANUAL_EN.md",
            "fr": "MANUEL_UTILISATEUR_FR.md",
        }.get(language, "BENUTZERHANDBUCH_DE.md")

        roots: list[Path] = [Path(__file__).resolve().parents[1]]
        if getattr(sys, "frozen", False):
            roots.extend(
                [
                    Path(sys.executable).resolve().parent,
                    Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)),
                ]
            )
        candidates = [root / "docs" / filename for root in roots]
        # Deutsch ist immer der letzte sichere Fallback.
        candidates.extend(root / "docs" / "BENUTZERHANDBUCH_DE.md" for root in roots)
        return list(dict.fromkeys(candidates))

    def _open_manual(self) -> None:
        manual = next((path for path in self._manual_candidates() if path.is_file()), None)
        if manual is None:
            QMessageBox.warning(
                self,
                t("help.manual_missing_title"),
                t("help.manual_missing_body"),
            )
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(manual))):
            QMessageBox.warning(
                self,
                t("help.manual_open_error_title"),
                t("help.manual_open_error_body", path=str(manual)),
            )

    def _add_start_tab(self) -> None:
        page, layout = _scroll_page()
        layout.addWidget(_card(t("help.quickstart_title"), t("help.quickstart_body")))
        layout.addWidget(_card(t("help.manual_title"), t("help.manual_body")))
        layout.addWidget(_card(t("help.dashboard_title"), t("help.dashboard_body")))
        layout.addWidget(_card(t("help.mode_title"), t("help.mode_body")))
        layout.addStretch()
        self.tabs.addTab(page, t("help.start_tab"))

    def _add_data_entry_tab(self) -> None:
        page, layout = _scroll_page()
        layout.addWidget(
            _card(t("help.data_entry.workflow_title"), t("help.data_entry.workflow_body"))
        )
        layout.addWidget(
            _card(t("help.data_entry.units_title"), t("help.data_entry.units_body"))
        )
        layout.addWidget(
            _card(t("help.data_entry.persistence_title"), t("help.data_entry.persistence_body"))
        )
        layout.addWidget(
            _card(t("help.data_entry.images_title"), t("help.data_entry.images_body"))
        )
        layout.addStretch()
        self.tabs.addTab(page, t("help.data_entry.tab"))

    def _add_rotation_tab(self) -> None:
        page, layout = _scroll_page()
        layout.addWidget(
            _card(t("help.rotation.workflow_title"), t("help.rotation.workflow_body"))
        )
        layout.addWidget(
            _card(t("help.rotation.score_title"), t("help.rotation.score_body"))
        )
        layout.addWidget(
            _card(t("help.rotation.reroll_title"), t("help.rotation.reroll_body"))
        )
        layout.addWidget(
            _card(t("help.rotation.random_title"), t("help.rotation.random_body"))
        )
        layout.addWidget(
            _card(t("help.rotation.pins_title"), t("help.rotation.pins_body"))
        )
        layout.addStretch()
        self.tabs.addTab(page, t("help.rotation.tab"))

    def _add_rules_tab(self) -> None:
        page, layout = _scroll_page()
        layout.addWidget(
            _card(t("help.rules.principle_title"), t("help.rules.principle_body"))
        )
        layout.addWidget(
            _card(t("help.rules.levels_title"), t("help.rules.levels_body"))
        )
        layout.addWidget(
            _card(t("help.rules.vac_shimmer_title"), t("help.rules.vac_shimmer_body"))
        )
        layout.addStretch()
        self.tabs.addTab(page, t("help.rules.tab"))

    def _add_auto_tab(self) -> None:
        page, layout = _scroll_page()
        layout.addWidget(
            _card(t("help.auto.decision_title"), t("help.auto.decision_body"))
        )
        layout.addWidget(
            _card(t("help.auto.explain_title"), t("help.auto.explain_body"))
        )
        layout.addStretch()
        self.tabs.addTab(page, t("help.auto.tab"))

    def _add_service_tab(self) -> None:
        page, layout = _scroll_page()
        layout.addWidget(
            _card(t("help.service.locks_title"), t("help.service.locks_body"))
        )
        layout.addWidget(
            _card(t("help.service.end_title"), t("help.service.end_body"))
        )
        layout.addWidget(
            _card(t("help.service.dry_risk_title"), t("help.service.dry_risk_body"))
        )
        layout.addStretch()
        self.tabs.addTab(page, t("help.service.tab"))

    def _add_consumption_tab(self) -> None:
        page, layout = _scroll_page()
        layout.addWidget(
            _card(t("help.consumption.stock_title"), t("help.consumption.stock_body"))
        )
        layout.addWidget(
            _card(t("help.consumption.optional_title"), t("help.consumption.optional_body"))
        )
        layout.addStretch()
        self.tabs.addTab(page, t("help.consumption.tab"))

    def _add_research_tab(self) -> None:
        page, layout = _scroll_page()
        layout.addWidget(
            _card(t("help.research.lookup_title"), t("help.research.lookup_body"))
        )
        layout.addWidget(
            _card(t("help.research.sources_title"), t("help.research.sources_body"))
        )
        layout.addWidget(
            _card(t("help.research.overlay_title"), t("help.research.overlay_body"))
        )
        layout.addStretch()
        self.tabs.addTab(page, t("help.research.tab"))

    def _add_glossary_tab(self) -> None:
        page, layout = _scroll_page()
        grid = QGridLayout()
        grid.setColumnStretch(1, 1)
        terms = [
            ("Sheen", t("ui.help_widget.glossary_sheen_desc")),
            ("Shimmer", t("ui.help_widget.glossary_shimmer_desc")),
            ("Feathering", t("ui.help_widget.glossary_feathering_desc")),
            ("Grail", t("ui.help_widget.glossary_grail_desc")),
            ("Override", t("ui.help_widget.glossary_override_desc")),
            ("Safety Timer", t("ui.help_widget.glossary_safety_desc")),
            ("EDC", t("ui.help_widget.glossary_edc_desc")),
            ("Vac / Vacuum", t("ui.help_widget.glossary_vac_desc")),
            (
                "💍 " + t("ui.help_widget.glossary_fixed_term"),
                t("ui.help_widget.glossary_fixed_desc"),
            ),
            (
                "⭐ " + t("ui.help_widget.glossary_must_term"),
                t("ui.help_widget.glossary_must_desc"),
            ),
            (
                t("ui.help_widget.glossary_hard_soft_term"),
                t("ui.help_widget.glossary_hard_soft_desc"),
            ),
            ("Reroll", t("ui.help_widget.glossary_reroll_desc")),
        ]
        for row, (term, description) in enumerate(terms):
            term_label = QLabel(f"<b>{term}</b>")
            description_label = QLabel(description)
            description_label.setWordWrap(True)
            grid.addWidget(term_label, row, 0)
            grid.addWidget(description_label, row, 1)
        box = QGroupBox(t("ui.help_widget.glossar_3625192c"))
        box.setProperty(
            "help_search_text",
            _plain_text(" ".join(f"{term} {description}" for term, description in terms)),
        )
        box.setLayout(grid)
        layout.addWidget(box)
        layout.addStretch()
        self.tabs.addTab(page, t("ui.help_widget.glossar_3625192c"))
