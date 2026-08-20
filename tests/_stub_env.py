"""Bedingte Umgebungs-Stubs für Sandbox-Läufe (v0.3.02).

Eine Quelle für den SQLAlchemy-Stub (und optional einen PySide6-Minimal-
Stub), genutzt von tests/conftest.py und tools/import_smoke.py. In der CI
mit echten Paketen sind beide Funktionen No-ops.
"""
from __future__ import annotations

import sys
import types


def install_sqlalchemy_stub() -> bool:
    """SQLAlchemy-Stub installieren, falls das echte Paket fehlt.

    Rückgabe True, wenn der Stub aktiv ist.
    """
    try:  # pragma: no cover - Umgebungsweiche
        import sqlalchemy  # noqa: F401
    except ImportError:  # pragma: no cover
        import types
        from datetime import datetime as _dt

        class _Sentinel:
            def __init__(self, *a, **kw):
                self.default = kw.get("default")
            def __set_name__(self, owner, name):
                self._name = name
            # Spalten-Ausdrücke wie InkLoad.loaded_date.desc() dürfen im Stub nicht
            # crashen; die Fake-Query ignoriert die Sortier-Argumente ohnehin.
            def desc(self):
                return self
            def asc(self):
                return self

        def _col(*a, **kw):
            return _Sentinel(*a, **kw)

        class _MappedMeta(type):
            def __getitem__(cls, item):
                return object

        class Mapped(metaclass=_MappedMeta):
            pass

        class DeclarativeBase:
            def __init_subclass__(cls, **kw):
                super().__init_subclass__(**kw)
            def __init__(self, **kw):
                for klass in type(self).__mro__:
                    for name, val in vars(klass).items():
                        if isinstance(val, _Sentinel) and not hasattr(self, "_init_" + name):
                            default = val.default
                            setattr(self, name, [] if default is None and name.endswith("s") and getattr(val, "_rel", False) else default)
                for k, v in kw.items():
                    setattr(self, k, v)
            def __getattr__(self, name):
                # Unbekannte Modellattribute verhalten sich wie ungesetzte Spalten.
                if name.startswith("_"):
                    raise AttributeError(name)
                return None

        def _relationship(*a, **kw):
            s = _Sentinel(default=None)
            s._rel = True
            return s

        sa = types.ModuleType("sqlalchemy")
        for _n in ("Column", "Integer", "String", "Float", "Boolean",
                   "DateTime", "Text", "ForeignKey"):
            setattr(sa, _n, _col)
        sa.create_engine = lambda *a, **kw: None
        sa.text = lambda q: q
        orm = types.ModuleType("sqlalchemy.orm")
        orm.DeclarativeBase = DeclarativeBase
        orm.Mapped = Mapped
        orm.mapped_column = _col
        orm.relationship = _relationship
        orm.sessionmaker = lambda *a, **kw: (lambda: None)
        orm.Session = object
        orm.close_all_sessions = lambda: None
        sa.orm = orm
        sys.modules["sqlalchemy"] = sa
        sys.modules["sqlalchemy.orm"] = orm

    else:
        return False
    return True


def install_pyside6_stub() -> bool:
    """PySide6-Minimal-Stub (nur für Import-Smoke, KEINE GUI-Funktion).

    Liefert für beliebige Qt-Namen eine Dummy-Klasse; Signal ist aufrufbar.
    Rückgabe True, wenn der Stub aktiv ist.
    """
    try:  # pragma: no cover - Umgebungsweiche
        import PySide6  # noqa: F401
        return False
    except ImportError:  # pragma: no cover
        class _Any:
            def __init__(self, *a, **k):
                pass

            def __call__(self, *a, **k):
                return _Any()

            def __getattr__(self, name):
                return _Any()

        def _module(name: str) -> types.ModuleType:
            mod = types.ModuleType(name)
            mod.__getattr__ = lambda attr, _A=_Any: _A  # PEP 562
            return mod

        qtw = _module("PySide6.QtWidgets")
        qtc = _module("PySide6.QtCore")
        qtg = _module("PySide6.QtGui")
        qtc.Signal = lambda *a, **k: _Any()
        qtc.Slot = lambda *a, **k: (lambda fn: fn)
        pys = types.ModuleType("PySide6")
        pys.QtWidgets, pys.QtCore, pys.QtGui = qtw, qtc, qtg
        sys.modules.update({
            "PySide6": pys,
            "PySide6.QtWidgets": qtw,
            "PySide6.QtCore": qtc,
            "PySide6.QtGui": qtg,
        })
        return True
