"""
OnboardingWizard – 4-Schritt-Dialog beim ersten Start mit leerer Datenbank.

Erklärt die zwingende Reihenfolge:
  1. Tinte anlegen  →  2. Füller anlegen  →  3. Tinte einfüllen  →  4. Fertig

Der Wizard öffnet per CTA-Button direkt die passenden Dialoge.
Nach Abschluss wird ``onboarding_completed`` in AppSettings gesetzt.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QWidget, QProgressBar, QFrame,
)

from database.db import get_session
from database.models import AppSettings
from i18n.translator import t


# ── Hilfsfunktion: Onboarding-Status ─────────────────────────────────────────

def should_show_wizard() -> bool:
    """True wenn Wizard noch nicht abgeschlossen und DB leer ist."""
    session = get_session()
    try:
        done = AppSettings.get(session, "onboarding_completed", "0")
        if done == "1":
            return False
        # Zeige Wizard nur wenn wirklich gar nichts angelegt ist
        from database.models import Pen, Ink
        has_pens = session.query(Pen).first() is not None
        has_inks = session.query(Ink).first() is not None
        return not has_pens and not has_inks
    finally:
        session.close()


def mark_wizard_done() -> None:
    """Wizard als abgeschlossen markieren."""
    session = get_session()
    try:
        AppSettings.set(session, "onboarding_completed", "1")
        session.commit()
    finally:
        session.close()


# ── Einzelne Wizard-Seite ─────────────────────────────────────────────────────

def _make_page(
    step: int,
    total: int,
    icon: str,
    title: str,
    body: str,
    action_label: str | None = None,
) -> tuple[QWidget, QPushButton | None]:
    """Erstellt eine Wizard-Seite. Gibt (Widget, action_button) zurück."""
    page = QWidget()
    vl = QVBoxLayout(page)
    vl.setSpacing(16)
    vl.setContentsMargins(40, 32, 40, 24)

    # Schritt-Indikator
    step_lbl = QLabel(t("tour.wizard.step_indicator", step=step, total=total))
    step_lbl.setStyleSheet("font-size:12px; color:#95a5a6;")
    vl.addWidget(step_lbl)

    # Icon
    icon_lbl = QLabel(icon)
    icon_lbl.setStyleSheet("font-size:52px;")
    icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    vl.addWidget(icon_lbl)

    # Titel
    title_lbl = QLabel(title)
    title_lbl.setStyleSheet("font-size:20px; font-weight:bold; color:#1e2a38;")
    title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    title_lbl.setWordWrap(True)
    vl.addWidget(title_lbl)

    # Trennlinie
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet("color:#d5dce6;")
    vl.addWidget(line)

    # Erklärungstext
    body_lbl = QLabel(body)
    body_lbl.setWordWrap(True)
    body_lbl.setStyleSheet("font-size:13px; color:#34495e; line-height:1.6;")
    body_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
    vl.addWidget(body_lbl)

    vl.addStretch()

    # Optionaler Action-Button
    action_btn = None
    if action_label:
        action_btn = QPushButton(action_label)
        action_btn.setStyleSheet(
            "background:#3498db; color:white; border:none;"
            " padding:10px 24px; border-radius:6px;"
            " font-weight:bold; font-size:13px;"
        )
        vl.addWidget(action_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    return page, action_btn


# ── Hauptdialog ───────────────────────────────────────────────────────────────

class OnboardingWizard(QDialog):
    """
    4-Schritt-Wizard für den ersten Start.

    Emittiert ``navigate_to(index)`` wenn der Nutzer per CTA-Button
    direkt in ein Modul springen will.
    """

    navigate_to = Signal(int)   # Modul-Index (0=Dashboard, 1=Pens, 2=Inks …)
    open_ink_dialog  = Signal()
    open_pen_dialog  = Signal()
    open_load_dialog = Signal()

    TOTAL_STEPS = 4

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("tour.wizard.window_title"))
        self.setMinimumSize(580, 520)
        self.setModal(True)
        self._setup_ui()
        self._go_to(0)

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # ── Fortschrittsbalken oben ───────────────────────────────────
        self._progress = QProgressBar()
        self._progress.setRange(0, self.TOTAL_STEPS)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(6)
        self._progress.setStyleSheet(
            "QProgressBar { border:none; background:#ecf0f1; }"
            "QProgressBar::chunk { background:#3498db; }"
        )
        root.addWidget(self._progress)

        # ── Seiten-Stack ──────────────────────────────────────────────
        self._stack = QStackedWidget()
        root.addWidget(self._stack, 1)

        # Seite 1: Willkommen
        p1, _ = _make_page(
            1, self.TOTAL_STEPS, "✒",
            t("tour.wizard.welcome_title"),
            t("tour.wizard.welcome_body"),
        )
        self._stack.addWidget(p1)

        # Seite 2: Erste Tinte
        p2, self._btn_ink = _make_page(
            2, self.TOTAL_STEPS, "🫙",
            t("tour.wizard.ink_title"),
            t("tour.wizard.ink_body"),
            t("tour.wizard.ink_button"),
        )
        if self._btn_ink:
            self._btn_ink.clicked.connect(self._on_add_ink)
        self._stack.addWidget(p2)

        # Seite 3: Ersten Füller
        p3, self._btn_pen = _make_page(
            3, self.TOTAL_STEPS, "✒",
            t("tour.wizard.pen_title"),
            t("tour.wizard.pen_body"),
            t("tour.wizard.pen_button"),
        )
        if self._btn_pen:
            self._btn_pen.clicked.connect(self._on_add_pen)
        self._stack.addWidget(p3)

        # Seite 4: Tinte einfüllen
        p4, self._btn_load = _make_page(
            4, self.TOTAL_STEPS, "🔄",
            t("tour.wizard.load_title"),
            t("tour.wizard.load_body"),
            t("tour.wizard.load_button"),
        )
        if self._btn_load:
            self._btn_load.clicked.connect(self._on_go_to_pens)
        self._stack.addWidget(p4)

        # ── Navigation unten ──────────────────────────────────────────
        nav = QHBoxLayout()
        nav.setContentsMargins(24, 12, 24, 20)

        self._btn_skip = QPushButton(t("tour.wizard.skip"))
        self._btn_skip.setStyleSheet("color:#7f8c8d; border:none; padding:8px;")
        self._btn_skip.clicked.connect(self._finish)
        nav.addWidget(self._btn_skip)

        nav.addStretch()

        self._btn_back = QPushButton(t("tour.wizard.back"))
        self._btn_back.setStyleSheet(
            "border:1px solid #bdc3c7; padding:8px 18px; border-radius:5px;"
            " color:#34495e; background:white;"
        )
        self._btn_back.clicked.connect(self._go_back)
        nav.addWidget(self._btn_back)

        self._btn_next = QPushButton(t("tour.wizard.next"))
        self._btn_next.setStyleSheet(
            "background:#27ae60; color:white; border:none;"
            " padding:8px 18px; border-radius:5px; font-weight:bold;"
        )
        self._btn_next.clicked.connect(self._go_next)
        nav.addWidget(self._btn_next)

        root.addLayout(nav)

    # ── Navigation ────────────────────────────────────────────────────

    def _go_to(self, index: int):
        self._stack.setCurrentIndex(index)
        self._progress.setValue(index + 1)
        self._btn_back.setVisible(index > 0)
        is_last = (index == self.TOTAL_STEPS - 1)
        self._btn_next.setText(t("tour.wizard.done") if is_last else t("tour.wizard.next"))
        self._btn_next.setStyleSheet(
            ("background:#27ae60;" if not is_last else "background:#2ecc71;")
            + " color:white; border:none; padding:8px 18px; border-radius:5px; font-weight:bold;"
        )

    def _go_next(self):
        idx = self._stack.currentIndex()
        if idx >= self.TOTAL_STEPS - 1:
            self._finish()
        else:
            self._go_to(idx + 1)

    def _go_back(self):
        idx = self._stack.currentIndex()
        if idx > 0:
            self._go_to(idx - 1)

    def _finish(self):
        mark_wizard_done()
        self.accept()

    # ── CTA-Buttons ───────────────────────────────────────────────────

    def _on_add_ink(self):
        """Tinte-Dialog öffnen und danach auf nächste Seite springen."""
        self.open_ink_dialog.emit()
        self._go_to(2)  # weiter zu "Füller anlegen"

    def _on_add_pen(self):
        """Füller-Dialog öffnen und danach auf nächste Seite."""
        self.open_pen_dialog.emit()
        self._go_to(3)  # weiter zu "Einfüllen"

    def _on_go_to_pens(self):
        """Zur Füllerverwaltung navigieren und Wizard schließen."""
        self.navigate_to.emit(1)   # index 1 = PenWidget
        self._finish()
