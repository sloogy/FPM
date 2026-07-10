"""Spotlight-Overlay für die App-Tour.

Liegt als vollflächiges Widget über dem Hauptfenster:
- dimmt die App ab,
- spart ein Rechteck um das Target-Widget aus (Spotlight),
- zeigt eine Erklär-Bubble mit Titel, Text und Nav-Buttons.

Robust: arbeitet ausschließlich mit normalem Alpha-Blending (4 Rechtecke
um das Target malen), kein `CompositionMode_Clear` – läuft so auf Linux
und Windows gleich.
"""
from __future__ import annotations

from ui.ui_scale import scale_px
from i18n.translator import t

from PySide6.QtCore import Qt, Signal, QRect, QEvent
from PySide6.QtGui import QPainter, QColor, QPen, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
)


class TourBubble(QFrame):
    """Erklär-Karte mit Titel, Text und Nav-Buttons."""
    next_clicked = Signal()
    back_clicked = Signal()
    skip_clicked = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("tourBubble")
        self.setStyleSheet("""
            QFrame#tourBubble {
                background: white;
                border: 1px solid #bdc3c7;
                border-radius: 12px;
            }
        """)
        self.setMinimumWidth(scale_px(360))
        self.setMaximumWidth(scale_px(460))

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 14)
        lay.setSpacing(10)

        self._title_lbl = QLabel()
        self._title_lbl.setWordWrap(True)
        self._title_lbl.setStyleSheet("font-size:15px; font-weight:bold; color:#2c3e50; border:none; background:transparent;")
        self._body_lbl = QLabel()
        self._body_lbl.setWordWrap(True)
        self._body_lbl.setTextFormat(Qt.TextFormat.RichText)
        self._body_lbl.setStyleSheet("color:#34495e; border:none; background:transparent;")

        lay.addWidget(self._title_lbl)
        lay.addWidget(self._body_lbl)

        nav = QHBoxLayout()
        nav.setSpacing(8)
        self._skip_btn = QPushButton(t("tour.buttons.abort"))
        self._skip_btn.setStyleSheet("color:#c0392b; border:1px solid #e6b0aa; padding:6px 10px; border-radius:5px; background:#fff5f5;")
        self._skip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._skip_btn.clicked.connect(self.skip_clicked)
        nav.addWidget(self._skip_btn)
        nav.addStretch()
        self._back_btn = QPushButton(t("tour.buttons.back"))
        self._back_btn.setStyleSheet("border:1px solid #bdc3c7; padding:6px 14px; border-radius:5px; color:#34495e; background:white;")
        self._back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._back_btn.clicked.connect(self.back_clicked)
        nav.addWidget(self._back_btn)
        self._next_btn = QPushButton(t("tour.buttons.next"))
        self._next_btn.setStyleSheet("background:#27ae60; color:white; border:none; padding:6px 16px; border-radius:5px; font-weight:bold;")
        self._next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._next_btn.clicked.connect(self.next_clicked)
        nav.addWidget(self._next_btn)
        lay.addLayout(nav)

    def update_content(self, title: str, body: str,
                       show_back: bool, is_last: bool,
                       next_label: str | None = None,
                       skip_label: str | None = None) -> None:
        self._title_lbl.setText(title)
        self._body_lbl.setText(body)
        self._back_btn.setVisible(show_back)
        self._next_btn.setText(next_label or (t("tour.buttons.done") if is_last else t("tour.buttons.next")))
        if skip_label is not None:
            self._skip_btn.setText(skip_label)
        else:
            self._skip_btn.setText(t("tour.buttons.finish_abort") if is_last else t("tour.buttons.abort"))
        self.adjustSize()


class SpotlightOverlay(QWidget):
    """Vollflächiges Tour-Overlay über dem Hauptfenster."""
    next_clicked = Signal()
    back_clicked = Signal()
    skip_clicked = Signal()

    DIM_COLOR = QColor(0, 0, 0, 170)
    HALO_COLOR = QColor("#3498db")
    HALO_WIDTH = 3
    HALO_PADDING = 8

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self._target_rect: QRect | None = None
        self._pass_through = False

        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Wichtig: Bubble und Abbruch-Button sind absichtlich Geschwister des
        # Overlays, nicht Kinder des Overlays. So bleiben sie auch dann klickbar,
        # wenn das Overlay in interaktiven Tour-Schritten Maus-Events an die App
        # darunter durchlässt (WA_TransparentForMouseEvents=True).
        self.bubble = TourBubble(parent)
        self.bubble.next_clicked.connect(self.next_clicked)
        self.bubble.back_clicked.connect(self.back_clicked)
        self.bubble.skip_clicked.connect(self.skip_clicked)
        self.bubble.hide()

        self._abort_btn = QPushButton("✕ " + t("tour.buttons.abort"), parent)
        self._abort_btn.setObjectName("tourAbortButton")
        self._abort_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._abort_btn.setToolTip(t("tour.buttons.abort_tooltip"))
        self._abort_btn.setStyleSheet("""
            QPushButton#tourAbortButton {
                background: #c0392b;
                color: white;
                border: none;
                border-radius: 7px;
                padding: 8px 14px;
                font-weight: bold;
            }
            QPushButton#tourAbortButton:hover { background: #a93226; }
        """)
        self._abort_btn.clicked.connect(self.skip_clicked)
        self._abort_btn.hide()

        # ESC beendet die Tour ebenfalls – wichtig, falls ein Ziel/Bubble ungünstig liegt.
        self._esc_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), parent)
        self._esc_shortcut.activated.connect(self.skip_clicked)
        self._esc_shortcut.setEnabled(False)

        if parent is not None:
            parent.installEventFilter(self)

        self.hide()

    def eventFilter(self, obj, event):
        if obj is self.parentWidget() and event.type() in (QEvent.Type.Resize, QEvent.Type.Show):
            self.resize(obj.size())
            self._position_bubble()
            self._position_abort_button()
            self.update()
        return super().eventFilter(obj, event)

    # ── öffentliche API ─────────────────────────────────────────────────
    def show_step(self, *, title: str, body: str,
                  target_rect: QRect | None,
                  show_back: bool, is_last: bool,
                  pass_through: bool = False,
                  next_label: str | None = None,
                  skip_label: str | None = None) -> None:
        self._target_rect = target_rect
        self._pass_through = pass_through
        # Maus-Events bei interaktiven Schritten durchlassen (außer auf der Bubble);
        # die Bubble bekommt Klicks trotzdem, weil sie ein eigenes Kind-Widget ist
        # und Qt das Hit-Testing pro Widget macht.
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, pass_through)
        self.bubble.update_content(title, body, show_back, is_last, next_label, skip_label)
        if self.parentWidget() is not None:
            self.resize(self.parentWidget().size())
        self.raise_()
        self.show()
        self._esc_shortcut.setEnabled(True)
        self.bubble.show()
        self._abort_btn.show()
        self._position_bubble()
        self._position_abort_button()
        # Reihenfolge ist wichtig: Overlay abdunkeln, Bubble/Abbruch darüber.
        self.bubble.raise_()
        self._abort_btn.raise_()
        self.update()

    def refresh_target(self, target_rect: QRect | None) -> None:
        """Nur das Spotlight-Rechteck aktualisieren (z.B. nach Resize/Re-Layout)."""
        self._target_rect = target_rect
        if self.parentWidget() is not None:
            self.resize(self.parentWidget().size())
        self._position_bubble()
        self._position_abort_button()
        self.update()

    def hide_overlay(self) -> None:
        self.hide()
        self.bubble.hide()
        self._abort_btn.hide()
        self._esc_shortcut.setEnabled(False)

    # ── Painting & Layout ───────────────────────────────────────────────
    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        tr = self._target_rect
        if tr is None or tr.isNull():
            p.fillRect(self.rect(), self.DIM_COLOR)
            return

        # Padding um das Target legen
        halo = tr.adjusted(-self.HALO_PADDING, -self.HALO_PADDING,
                           self.HALO_PADDING, self.HALO_PADDING)
        halo = halo.intersected(self.rect())

        # 4 Rechtecke außenherum abdunkeln – einfacher und plattform-stabil
        w, h = self.width(), self.height()
        # Oben
        if halo.top() > 0:
            p.fillRect(0, 0, w, halo.top(), self.DIM_COLOR)
        # Unten
        if halo.bottom() < h:
            p.fillRect(0, halo.bottom() + 1, w, h - halo.bottom() - 1, self.DIM_COLOR)
        # Links
        if halo.left() > 0:
            p.fillRect(0, halo.top(), halo.left(), halo.height(), self.DIM_COLOR)
        # Rechts
        if halo.right() < w:
            p.fillRect(halo.right() + 1, halo.top(),
                       w - halo.right() - 1, halo.height(), self.DIM_COLOR)

        # Rahmen um das Target
        pen = QPen(self.HALO_COLOR, self.HALO_WIDTH)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(halo, 8, 8)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_bubble()
        self._position_abort_button()

    def _position_bubble(self) -> None:
        self.bubble.adjustSize()
        bw, bh = self.bubble.width(), self.bubble.height()
        margin = 12

        if not self._target_rect or self._target_rect.isNull():
            # Zentriert
            x = (self.width() - bw) // 2
            y = (self.height() - bh) // 2
            self.bubble.move(max(margin, x), max(margin, y))
            return

        tr = self._target_rect
        # Bevorzugt unter dem Target; sonst drüber; sonst rechts; sonst links
        below_y = tr.bottom() + 20
        above_y = tr.top() - bh - 20
        x_centered = tr.x() + (tr.width() - bw) // 2

        if below_y + bh + margin <= self.height():
            x = max(margin, min(x_centered, self.width() - bw - margin))
            self.bubble.move(x, below_y)
        elif above_y >= margin:
            x = max(margin, min(x_centered, self.width() - bw - margin))
            self.bubble.move(x, above_y)
        else:
            # Notlösung: rechts oder links neben dem Target
            right_x = tr.right() + 20
            if right_x + bw + margin <= self.width():
                y = max(margin, min(tr.y(), self.height() - bh - margin))
                self.bubble.move(right_x, y)
            else:
                left_x = tr.left() - bw - 20
                y = max(margin, min(tr.y(), self.height() - bh - margin))
                self.bubble.move(max(margin, left_x), y)

    def _position_abort_button(self) -> None:
        """Permanenter Abbruch oben rechts, unabhängig von Bubble-Position."""
        self._abort_btn.adjustSize()
        margin = 14
        x = max(margin, self.width() - self._abort_btn.width() - margin)
        y = margin
        self._abort_btn.move(x, y)

    # Bubble darf Maus immer empfangen, auch wenn Overlay transparent
    def mousePressEvent(self, event):
        # Wenn pass_through aktiv ist, leitet Qt das ohnehin weiter; ansonsten
        # schlucken wir Klicks außerhalb der Bubble, damit der User die echte
        # UI in nicht-interaktiven Schritten nicht versehentlich bedient.
        if not self._pass_through:
            event.accept()
            return
        super().mousePressEvent(event)
