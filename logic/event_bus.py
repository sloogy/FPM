"""
AppEventBus – zentraler Qt-Signal-Bus für UI-Synchronisierung.

Löst das Session-Race-Problem: Widget A committed → emittet Signal →
alle bereits geöffneten Widgets die sich subscribt haben refreshen sich.

Nutzung
-------
Emittieren (nach session.commit()):
    from logic.event_bus import AppEventBus
    AppEventBus.instance().pens_changed.emit()

Subscriben (im Widget-Konstruktor oder _setup_ui):
    AppEventBus.instance().pens_changed.connect(self.refresh)

Verfügbare Signals
------------------
pens_changed   – Pen angelegt / bearbeitet / archiviert / gelöscht / befüllt / gereinigt
inks_changed   – Ink angelegt / bearbeitet / leer / archiviert / gelöscht
nibs_changed   – Nib angelegt / bearbeitet / gelöscht
papers_changed – Paper angelegt / bearbeitet / gelöscht
expenses_changed – Expense angelegt / geändert / gelöscht
all_changed    – Shortcut wenn unklar welche Entities betroffen sind

Design-Entscheidungen
---------------------
* Singleton über ``instance()`` – ein Bus für die gesamte Laufzeit.
* Kein Debouncing: Widgets sollen sofort reagieren. Wenn das bei großen
  Sammlungen zu Performance-Problemen führt, kann hier ein QTimer-Debounce
  ergänzt werden (emit → 50ms Timer → wirklich refreshen).
* Widgets die noch nicht instanziiert sind (Lazy Loading) empfangen keine
  Signals – das ist korrekt, da sie beim ersten Öffnen sowieso refresh()
  aufrufen.
"""
from __future__ import annotations

try:
    from PySide6.QtCore import QObject, Signal
except ModuleNotFoundError:  # pragma: no cover - used in headless CI/source audits without Qt
    class QObject:  # minimal fallback: enough for logic/service tests without UI
        pass

    class _BoundSignal:
        def __init__(self):
            self._slots = []

        def connect(self, slot):
            if callable(slot):
                self._slots.append(slot)

        def emit(self, *args, **kwargs):
            for slot in list(self._slots):
                try:
                    slot(*args, **kwargs)
                except TypeError:
                    slot()

    class _SignalDescriptor:
        def __init__(self, *args, **kwargs):
            self._name = None

        def __set_name__(self, owner, name):
            self._name = f"_{name}_fallback_signal"

        def __get__(self, instance, owner):
            if instance is None:
                return self
            if self._name is None:
                self._name = "_fallback_signal"
            sig = getattr(instance, self._name, None)
            if sig is None:
                sig = _BoundSignal()
                setattr(instance, self._name, sig)
            return sig

    def Signal(*args, **kwargs):
        return _SignalDescriptor(*args, **kwargs)


class AppEventBus(QObject):
    """Singleton-Signal-Bus. Immer über ``instance()`` ansprechen."""

    # Entity-spezifische Signals
    pens_changed     = Signal()
    inks_changed     = Signal()
    nibs_changed     = Signal()
    papers_changed   = Signal()
    expenses_changed = Signal()
    samples_changed  = Signal()

    # Bequemlichkeits-Signal wenn mehrere Entities betroffen sind
    all_changed      = Signal()

    _instance: AppEventBus | None = None

    @classmethod
    def instance(cls) -> "AppEventBus":
        """Gibt die Singleton-Instanz zurück. Thread-safe durch Qt-Mechanismus."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def emit_pens(self) -> None:
        """Hilfsmethode: pens_changed emittieren."""
        self.pens_changed.emit()

    def emit_inks(self) -> None:
        self.inks_changed.emit()

    def emit_nibs(self) -> None:
        self.nibs_changed.emit()

    def emit_papers(self) -> None:
        self.papers_changed.emit()

    def emit_expenses(self) -> None:
        self.expenses_changed.emit()

    def emit_samples(self) -> None:
        self.samples_changed.emit()

    def emit_all(self) -> None:
        """Alle Signals auf einmal – z.B. nach Factory Reset oder Import."""
        self.pens_changed.emit()
        self.inks_changed.emit()
        self.nibs_changed.emit()
        self.papers_changed.emit()
        self.expenses_changed.emit()
        self.samples_changed.emit()
        self.all_changed.emit()
