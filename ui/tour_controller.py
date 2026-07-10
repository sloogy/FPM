"""TourController – orchestriert die App-Tour.

Akt 1: Rundgang durch die 11 Sidebar-Reiter.
Akt 2: Geführter Erstkauf – Wishlist anlegen → bestellt → gekauft → Tinte → Vorschlag.

Tour ist überspringbar, neustartbar (Hilfe + Einstellungen), und merkt sich in
AppSettings ('onboarding_completed'), dass sie durchlaufen wurde.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional, Any

from PySide6.QtCore import QObject, Signal, QTimer, QRect, QPoint, QEvent
from PySide6.QtWidgets import QWidget

from ui.tour_overlay import SpotlightOverlay
from i18n.translator import t


# ── Schritt-Datenklasse ──────────────────────────────────────────────────────
@dataclass
class TourStep:
    title: str
    body: str
    page_index: Optional[int] = None
    # Liefert das hervorzuhebende Widget; None = ganzes Fenster (zentrierte Bubble)
    target_resolver: Optional[Callable[[Any], Optional[QWidget]]] = None
    # Aktion beim Klick auf "Weiter" VOR dem Wechsel zum nächsten Schritt
    on_next: Optional[Callable[[Any], None]] = None
    next_label: Optional[str] = None
    # Klicks durchs Overlay an die echte UI durchlassen
    pass_through: bool = False
    # Vor dem Anzeigen ausführen (z.B. spezielle Seitenvorbereitung)
    on_enter: Optional[Callable[[Any], None]] = None


# ── Helper: AppSettings-Flag lesen/setzen ────────────────────────────────────
def should_show_tour() -> bool:
    """Tour zeigen, wenn DB leer ist und Flag noch nicht gesetzt."""
    try:
        from database.db import get_session
        from database.models import AppSettings, Pen, Ink, Nib
    except Exception:
        return False
    session = get_session()
    try:
        done = AppSettings.get(session, "onboarding_completed", "0")
        if str(done) == "1":
            return False
        # Wenn schon Daten da sind, gehen wir davon aus, dass die Tour nicht erneut soll
        if session.query(Pen).first() or session.query(Ink).first() or session.query(Nib).first():
            return False
        return True
    finally:
        session.close()


def mark_tour_done() -> None:
    try:
        from database.db import get_session
        from database.models import AppSettings
    except Exception:
        return
    session = get_session()
    try:
        AppSettings.set(session, "onboarding_completed", "1")
        session.commit()
    finally:
        session.close()


def reset_tour() -> None:
    """Onboarding-Flag zurücksetzen, damit die Tour beim Start oder per Hand neu kommt."""
    try:
        from database.db import get_session
        from database.models import AppSettings
    except Exception:
        return
    session = get_session()
    try:
        AppSettings.set(session, "onboarding_completed", "0")
        session.commit()
    finally:
        session.close()


# ── Walkthrough-Helfer (Akt 2) ───────────────────────────────────────────────
def _open_wishlist_add(mw) -> None:
    """Wishlist-Reiter aktivieren und 'Wunsch anlegen'-Dialog öffnen."""
    mw._navigate(7)
    widget = mw._ensure_widget(7)
    if hasattr(widget, "_add"):
        try: widget._add()
        except Exception: pass


def _open_ink_add(mw) -> None:
    """Tinten-Reiter aktivieren und Dialog öffnen (bestehender Helper)."""
    if hasattr(mw, "_open_ink_add_dialog"):
        mw._open_ink_add_dialog()


def _run_first_rotation(mw) -> None:
    """Rotation-Reiter aktivieren und Vorschläge generieren, falls Aktion vorhanden."""
    mw._navigate(5)
    widget = mw._ensure_widget(5)
    # Versuche eine generierende Methode zu finden – Engine-Felder bleiben kompatibel
    for name in ("_refresh_suggestions", "_run", "_generate", "_load_suggestions", "refresh"):
        fn = getattr(widget, name, None)
        if callable(fn):
            try: fn()
            except Exception: pass
            return


# ── Schritt-Liste bauen ──────────────────────────────────────────────────────
def build_steps() -> list[TourStep]:
    """11 Reiter-Stops + geführter Erstkauf.

    Alle sichtbaren Tour-Texte laufen über i18n, damit die Introduction/Tour
    die aktive Sprache (de/en/fr) wirklich respektiert.
    """
    def page(i):
        return lambda mw: mw._ensure_widget(i)

    def step(key: str, page_index: int | None = None, target=None, **kwargs) -> TourStep:
        return TourStep(
            title=t(f"tour.steps.{key}.title"),
            body=t(f"tour.steps.{key}.body"),
            page_index=page_index,
            target_resolver=target,
            **kwargs,
        )

    steps: list[TourStep] = [
        step("welcome", 0),
        step("dashboard", 0, page(0)),
        step("pens", 1, page(1)),
        step("inks", 2, page(2)),
        step("nibs", 3, page(3)),
        step("paper", 4, page(4)),
        step("rotation", 5, page(5)),
        step("expenses", 6, page(6)),
        step("wishlist", 7, page(7)),
        step("rules", 8, page(8)),
        step("help", 9, page(9)),
        step("settings", 10, page(10)),
        step("first_purchase", 7, page(7)),
        step(
            "wishlist_add", 7, page(7),
            next_label=t("tour.buttons.open_dialog"),
            on_next=_open_wishlist_add,
        ),
        step("wishlist_status", 7, page(7), pass_through=True),
        step(
            "ink_add", 2, page(2),
            next_label=t("tour.buttons.open_dialog"),
            on_next=_open_ink_add,
        ),
        step(
            "rotation_run", 5, page(5),
            next_label=t("tour.buttons.generate"),
            on_next=_run_first_rotation,
        ),
        step("finished", 0),
    ]
    return steps

# ── Controller ───────────────────────────────────────────────────────────────
class TourController(QObject):
    """Steuert die Tour über Schritte hinweg."""
    finished = Signal()

    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        self.steps: list[TourStep] = []
        self.idx: int = 0
        self.overlay = SpotlightOverlay(main_window)
        self.overlay.next_clicked.connect(self.next_step)
        self.overlay.back_clicked.connect(self.prev_step)
        self.overlay.skip_clicked.connect(self.skip)
        self.main_window.installEventFilter(self)

    def start(self, steps: Optional[list[TourStep]] = None) -> None:
        self.steps = steps or build_steps()
        self.idx = 0
        self._show_current()

    def eventFilter(self, obj, event):
        if obj is self.main_window and event.type() in (QEvent.Type.Resize, QEvent.Type.Show, QEvent.Type.LayoutRequest):
            if self.overlay.isVisible() and self.steps and 0 <= self.idx < len(self.steps):
                QTimer.singleShot(0, lambda: self._render_step(self.steps[self.idx]))
        return super().eventFilter(obj, event)

    # ── Navigation ──────────────────────────────────────────────────────
    def next_step(self) -> None:
        if not self.steps:
            return
        step = self.steps[self.idx]
        # Bei Aktions-Schritten Overlay vorher verstecken, damit Dialoge sichtbar sind.
        if step.on_next:
            self.overlay.hide_overlay()
            try:
                step.on_next(self.main_window)
            except Exception:
                pass
        self.idx += 1
        if self.idx >= len(self.steps):
            self._finish()
            return
        self._show_current()

    def prev_step(self) -> None:
        if self.idx > 0:
            self.idx -= 1
            self._show_current()

    def skip(self) -> None:
        self._finish()

    # ── Rendering ───────────────────────────────────────────────────────
    def _show_current(self) -> None:
        if self.idx < 0 or self.idx >= len(self.steps):
            self._finish()
            return
        step = self.steps[self.idx]

        # Sidebar wechseln
        if step.page_index is not None:
            try:
                self.main_window._navigate(step.page_index)
            except Exception:
                pass

        # on_enter darf z.B. Daten vorbereiten
        if step.on_enter:
            try: step.on_enter(self.main_window)
            except Exception: pass

        # Layout etablieren lassen, dann Spotlight rendern
        QTimer.singleShot(120, lambda: self._render_step(step))

    def _render_step(self, step: TourStep) -> None:
        target_rect: Optional[QRect] = None
        if step.target_resolver is not None:
            try:
                target = step.target_resolver(self.main_window)
                if target is not None and target.isVisible():
                    top_left = target.mapTo(self.main_window, QPoint(0, 0))
                    target_rect = QRect(top_left, target.size())
            except Exception:
                target_rect = None

        is_last = (self.idx == len(self.steps) - 1)
        show_back = self.idx > 0 and not bool(step.on_next)
        self.overlay.show_step(
            title=step.title,
            body=step.body,
            target_rect=target_rect,
            show_back=show_back,
            is_last=is_last,
            pass_through=step.pass_through,
            next_label=step.next_label,
        )

    def _finish(self) -> None:
        self.overlay.hide_overlay()
        mark_tour_done()
        self.finished.emit()
