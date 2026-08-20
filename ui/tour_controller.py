"""TourController – orchestriert die App-Tour.

Akt 1: Rundgang durch die 11 Sidebar-Reiter.
Akt 2: Geführter Erstkauf – Wishlist anlegen → bestellt → gekauft → Tinte → Vorschlag.

Tour ist überspringbar, neustartbar (Hilfe + Einstellungen), und merkt sich in
AppSettings ('onboarding_completed'), dass sie durchlaufen wurde.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Any

from PySide6.QtCore import QObject, Signal, QTimer, QRect, QPoint, QEvent
from PySide6.QtWidgets import QMessageBox, QWidget

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
    # ``False`` bedeutet: Aktion wurde abgebrochen/fehlgeschlagen.
    on_next: Optional[Callable[[Any], bool | None]] = None
    next_label: Optional[str] = None
    # Klicks durchs Overlay an die echte UI durchlassen
    pass_through: bool = False
    # Vor dem Anzeigen ausführen (z.B. spezielle Seitenvorbereitung)
    on_enter: Optional[Callable[[Any], None]] = None
    # "expert" / "simple" / "original"; gilt vor der Seitennavigation.
    mode: Optional[str] = None
    step_id: str = ""


def _inventory_counts() -> tuple[int, int]:
    from database.db import get_session
    from database.repositories import InkRepository, PenRepository

    session = get_session()
    try:
        return InkRepository(session).count(), PenRepository(session).count()
    finally:
        session.close()


# ── Helper: AppSettings-Flag lesen/setzen ────────────────────────────────────
def should_show_tour() -> bool:
    """Tour zeigen, wenn sie erzwungen wurde oder die Sammlung noch leer ist."""
    try:
        from database.db import get_session
        from database.models import AppSettings, Pen, Ink, Nib
    except ImportError:
        return False
    session = get_session()
    try:
        forced = AppSettings.get(session, "onboarding_force_next_start", "0")
        if str(forced) == "1":
            return True
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
    except ImportError:
        return
    session = get_session()
    try:
        AppSettings.set(session, "onboarding_completed", "1")
        AppSettings.set(session, "onboarding_force_next_start", "0")
        session.commit()
    finally:
        session.close()


def reset_tour() -> None:
    """Tour beim nächsten Start unabhängig vom Datenbestand erzwingen."""
    try:
        from database.db import get_session
        from database.models import AppSettings
    except ImportError:
        return
    session = get_session()
    try:
        AppSettings.set(session, "onboarding_completed", "0")
        AppSettings.set(session, "onboarding_force_next_start", "1")
        session.commit()
    finally:
        session.close()


# ── Walkthrough-Helfer ───────────────────────────────────────────────────────
def _open_ink_add(mw) -> bool:
    return bool(mw._open_ink_add_dialog())


def _open_pen_add(mw) -> bool:
    return bool(mw._open_pen_add_dialog())


def _offer_second_pen(mw) -> bool:
    answer = QMessageBox.question(
        mw,
        t("tour.second_pen.question_title"),
        t("tour.second_pen.question_body"),
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.Yes,
    )
    if answer == QMessageBox.StandardButton.No:
        return True
    return bool(mw._open_pen_add_dialog())


def _rotation_widget(mw):
    mw._navigate(5)
    return mw._ensure_widget(5)


def _generate_rotation(mw) -> bool:
    widget = _rotation_widget(mw)
    generate = getattr(widget, "generate_suggestions", None)
    if not callable(generate):
        generate = getattr(widget, "_generate", None)
    return bool(generate()) if callable(generate) else False


def _apply_first_rotation(mw) -> bool:
    widget = _rotation_widget(mw)
    if not getattr(widget, "_last_suggestions", None):
        if not _generate_rotation(mw):
            return False
    apply_first = getattr(widget, "apply_first_suggestion", None)
    if callable(apply_first):
        return bool(apply_first())
    apply_row = getattr(widget, "_apply_suggestion", None)
    return bool(apply_row(0)) if callable(apply_row) else False


def execute_step_action(step: TourStep, main_window: Any) -> bool:
    """Führt eine Tour-Aktion aus; Abbruch und Fehler halten den Schritt offen."""
    if step.on_next is None:
        return True
    try:
        return step.on_next(main_window) is not False
    except Exception:
        return False


# ── Schritt-Liste bauen ──────────────────────────────────────────────────────
def build_steps() -> list[TourStep]:
    """Modulrunde zuerst, danach geführte Datenanlage und echte Rotation."""

    def page(index: int):
        return lambda mw: mw._ensure_widget(index)

    def rotation_target(name: str):
        return lambda mw: getattr(mw._ensure_widget(5), name, mw._ensure_widget(5))

    def first_apply_target(mw):
        widget = mw._ensure_widget(5)
        table = getattr(widget, "sug_table", None)
        if table is not None and table.rowCount() > 0:
            button = table.cellWidget(0, 6)
            if button is not None:
                return button
        return table or widget

    def step(key: str, page_index: int | None = None, target=None, **kwargs) -> TourStep:
        return TourStep(
            title=t(f"tour.steps.{key}.title"),
            body=t(f"tour.steps.{key}.body"),
            page_index=page_index,
            target_resolver=target,
            step_id=key,
            **kwargs,
        )

    try:
        ink_count, pen_count = _inventory_counts()
    except Exception:
        ink_count = pen_count = 0

    steps: list[TourStep] = [
        step("welcome", 0, page(0), mode="original"),
        step("dashboard", 0, page(0)),
        step("pens", 1, page(1)),
        step("inks", 2, page(2)),
        step("rotation", 5, page(5)),
        step("help", 9, page(9)),
        step("settings", 10, page(10)),
        step("expert_intro", 3, page(3), mode="expert"),
        step("nibs", 3, page(3), mode="expert"),
        step("paper", 4, page(4), mode="expert"),
        step("writing_samples", 12, page(12), mode="expert"),
        step("wishlist", 7, page(7), mode="expert"),
        step("expenses", 6, page(6), mode="expert"),
        step("statistics", 11, page(11), mode="expert"),
        step("enthusiast_lab", 13, page(13), mode="expert"),
        step("rules", 8, page(8), mode="expert"),
        step("setup_intro", 2, page(2), mode="original"),
    ]

    if ink_count == 0:
        steps.extend(
            [
                step(
                    "ink_add",
                    2,
                    page(2),
                    next_label=t("tour.buttons.open_dialog"),
                    on_next=_open_ink_add,
                ),
                step("ink_created", 2, page(2)),
            ]
        )

    if pen_count == 0:
        steps.extend(
            [
                step(
                    "pen_add",
                    1,
                    page(1),
                    next_label=t("tour.buttons.open_dialog"),
                    on_next=_open_pen_add,
                ),
                step("pen_created", 1, page(1)),
            ]
        )

    if pen_count < 2:
        steps.append(
            step(
                "second_pen",
                1,
                page(1),
                next_label=t("tour.buttons.optional_pen"),
                on_next=_offer_second_pen,
            )
        )

    steps.extend(
        [
            step("rotation_setup", 5, page(5)),
            step(
                "rotation_generate",
                5,
                rotation_target("generate_btn"),
                next_label=t("tour.buttons.generate"),
                on_next=_generate_rotation,
            ),
            step("rotation_result", 5, rotation_target("sug_table")),
            step(
                "rotation_apply",
                5,
                first_apply_target,
                next_label=t("tour.buttons.apply_suggestion"),
                on_next=_apply_first_rotation,
            ),
            step("rotation_active", 5, rotation_target("cur_table")),
            step("finished", 0, page(0)),
        ]
    )
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
        self._original_mode = "simple"
        self.overlay = SpotlightOverlay(main_window)
        self.overlay.next_clicked.connect(self.next_step)
        self.overlay.back_clicked.connect(self.prev_step)
        self.overlay.skip_clicked.connect(self.skip)
        self.main_window.installEventFilter(self)

    def start(self, steps: Optional[list[TourStep]] = None) -> None:
        from logic.app_mode import get_app_mode

        self._original_mode = get_app_mode()
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
            if not execute_step_action(step, self.main_window):
                QTimer.singleShot(120, self._show_current)
                return
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

    def _set_step_mode(self, mode: str | None) -> None:
        if not mode:
            return
        target_mode = self._original_mode if mode == "original" else mode
        setter = getattr(self.main_window, "set_navigation_mode", None)
        if callable(setter):
            setter(target_mode)

    # ── Rendering ───────────────────────────────────────────────────────
    def _show_current(self) -> None:
        if self.idx < 0 or self.idx >= len(self.steps):
            self._finish()
            return
        step = self.steps[self.idx]

        self._set_step_mode(step.mode)
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

    def _restore_original_mode(self) -> None:
        setter = getattr(self.main_window, "set_navigation_mode", None)
        if callable(setter):
            try:
                setter(self._original_mode)
            except Exception:
                pass

    def _finish(self) -> None:
        self.overlay.hide_overlay()
        self._restore_original_mode()
        mark_tour_done()
        self.finished.emit()
