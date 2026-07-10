"""Geführter Rundgang und interaktive Ersteinrichtung.

Ablauf auf einer frischen Installation:
1. Alltagsmodule kennenlernen.
2. Expertenmodule am Schluss der Modulrunde ansehen.
3. Gemeinsam eine Tinte und ein bis zwei Füller anlegen.
4. Einen echten Rotationsvorschlag erzeugen und übernehmen.

Die Tour verändert den Navigationsmodus nur vorübergehend und stellt den
ursprünglichen Modus beim Beenden oder Abbrechen wieder her.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from PySide6.QtCore import QEvent, QObject, QPoint, QRect, QTimer, Signal
from PySide6.QtWidgets import QMessageBox, QWidget

from i18n.translator import t
from ui.tour_overlay import SpotlightOverlay


@dataclass
class TourStep:
    title: str
    body: str
    page_index: Optional[int] = None
    target_resolver: Optional[Callable[[Any], Optional[QWidget]]] = None
    # ``False`` bedeutet: Aktion wurde abgebrochen/fehlgeschlagen, Schritt bleibt aktiv.
    on_next: Optional[Callable[[Any], bool | None]] = None
    next_label: Optional[str] = None
    pass_through: bool = False
    on_enter: Optional[Callable[[Any], None]] = None
    # "expert" / "simple" / "original"; wird vor der Seitennavigation angewendet.
    mode: Optional[str] = None
    step_id: str = ""


def _inventory_counts() -> tuple[int, int]:
    from database.db import get_session
    from database.models import Ink, Pen

    session = get_session()
    try:
        return session.query(Ink).count(), session.query(Pen).count()
    finally:
        session.close()


def should_show_tour() -> bool:
    """Zeigt die Tour, solange der Erststart nicht beendet/übersprungen wurde."""
    try:
        from database.db import get_session
        from database.models import AppSettings

        session = get_session()
        try:
            return str(AppSettings.get(session, "onboarding_completed", "0")) != "1"
        finally:
            session.close()
    except Exception:
        return False


def mark_tour_done() -> None:
    try:
        from database.db import get_session
        from database.models import AppSettings

        session = get_session()
        try:
            AppSettings.set(session, "onboarding_completed", "1")
        finally:
            session.close()
    except Exception:
        return


def reset_tour() -> None:
    """Setzt nur das Tour-Flag zurück; vorhandene Sammlung bleibt erhalten."""
    try:
        from database.db import get_session
        from database.models import AppSettings

        session = get_session()
        try:
            AppSettings.set(session, "onboarding_completed", "0")
        finally:
            session.close()
    except Exception:
        return


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

    # 1) Modulrunde: zuerst die sichtbaren Alltagsmodule.
    steps: list[TourStep] = [
        step("welcome", 0, page(0), mode="original"),
        step("dashboard", 0, page(0)),
        step("pens", 1, page(1)),
        step("inks", 2, page(2)),
        step("rotation", 5, page(5)),
        step("help", 9, page(9)),
        step("settings", 10, page(10)),
        # 2) Expertenfunktionen bewusst am Schluss der Modulrunde.
        step("expert_intro", 3, page(3), mode="expert"),
        step("nibs", 3, page(3), mode="expert"),
        step("paper", 4, page(4), mode="expert"),
        step("writing_samples", 12, page(12), mode="expert"),
        step("wishlist", 7, page(7), mode="expert"),
        step("expenses", 6, page(6), mode="expert"),
        step("statistics", 11, page(11), mode="expert"),
        step("enthusiast_lab", 13, page(13), mode="expert"),
        step("rules", 8, page(8), mode="expert"),
        # Zurück zum ursprünglichen Modus, bevor echte Daten angelegt werden.
        step("setup_intro", 2, page(2), mode="original"),
    ]

    # 3) Gemeinsame Ersteinrichtung. Vorhandene Daten werden respektiert.
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

    # 4) Echte Rotation: erzeugen, verstehen, bewusst übernehmen.
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


class TourController(QObject):
    """Steuert die Tour über Seiten, Modi und modale Erfassungsdialoge hinweg."""

    finished = Signal()

    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        self.steps: list[TourStep] = []
        self.idx = 0
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
        if obj is self.main_window and event.type() in (
            QEvent.Type.Resize,
            QEvent.Type.Show,
            QEvent.Type.LayoutRequest,
        ):
            if self.overlay.isVisible() and self.steps and 0 <= self.idx < len(self.steps):
                QTimer.singleShot(0, lambda: self._render_step(self.steps[self.idx]))
        return super().eventFilter(obj, event)

    def next_step(self) -> None:
        if not self.steps:
            return
        step = self.steps[self.idx]
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

    def _show_current(self) -> None:
        if self.idx < 0 or self.idx >= len(self.steps):
            self._finish()
            return
        step = self.steps[self.idx]

        self._set_step_mode(step.mode)
        if step.page_index is not None:
            self.main_window._navigate(step.page_index)

        if step.on_enter:
            step.on_enter(self.main_window)

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

        self.overlay.show_step(
            title=step.title,
            body=step.body,
            target_rect=target_rect,
            show_back=self.idx > 0 and not bool(step.on_next),
            is_last=self.idx == len(self.steps) - 1,
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
