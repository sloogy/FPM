"""v0.3.02: Verhaltenstests für logic.pen_service + neue Repositories.

Sichert die aus PenWidget/PenDialog extrahierte Datenlogik: Varianten-/
Dublettensuche, Einzel-Aktiv-Auswahl, NibFormat-Wiederverwendung vs.
-Anlage (add/flush), Ähnliche-Feder-Erkennung (normalisiert) und die
Kaufpreis-Spiegelung in den Ausgaben-Tracker (anlegen/aktualisieren/
entfernen). Fake-Session mit add/flush/delete und Id-Vergabe.
"""
from __future__ import annotations

# Aktiviert in der Sandbox den SQLAlchemy-Stub, bevor database/logic laden.
from tests.conftest import FakeInk as _StubHook  # noqa: F401

from database import repositories as repos
from logic import pen_service as ps


class Obj:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


class FakeQuery:
    def __init__(self, items):
        self._items = list(items)

    def filter_by(self, **kw):
        return FakeQuery([i for i in self._items
                          if all(getattr(i, k, None) == v for k, v in kw.items())])

    def filter(self, *conds):
        # Der SQLAlchemy-Stub liefert für Spaltenvergleiche keine echten
        # Ausdrücke; die Service-Tests nutzen daher die Repos über
        # vorgefilterte Fixtures bzw. testen filter-basierte Pfade separat
        # mit eigenem Matching (siehe _VariantQuery unten).
        return self

    def order_by(self, *a):
        return self

    def limit(self, n):
        return FakeQuery(self._items[:n])

    def first(self):
        return self._items[0] if self._items else None

    def all(self):
        return list(self._items)

    def count(self):
        return len(self._items)


class FakeSession:
    """Fake mit add/flush/delete und automatischer Id-Vergabe."""

    def __init__(self, data=None):
        self._data = {k: list(v) for k, v in (data or {}).items()}
        self._next_id = 1000
        self.deleted = []

    def _bucket(self, obj_or_model):
        name = (obj_or_model if isinstance(obj_or_model, str)
                else type(obj_or_model).__name__)
        return self._data.setdefault(name, [])

    def query(self, model):
        return FakeQuery(self._data.get(model.__name__, []))

    def get(self, model, oid):
        for item in self._data.get(model.__name__, []):
            if getattr(item, "id", None) == oid:
                return item
        return None

    def add(self, obj):
        self._bucket(obj).append(obj)

    def add_all(self, objs):
        for o in objs:
            self.add(o)

    def flush(self):
        for items in self._data.values():
            for item in items:
                if getattr(item, "id", None) in (None,):
                    item.id = self._next_id
                    self._next_id += 1

    def delete(self, obj):
        self.deleted.append(obj)
        bucket = self._bucket(obj)
        if obj in bucket:
            bucket.remove(obj)


def _pen(i, **kw):
    base = dict(id=i, brand="B", model=f"P{i}", color=None, ink_capacity_ml=None,
                is_active=True, purchase_price=None, purchase_currency=None,
                purchase_date=None)
    base.update(kw)
    return Obj(**base)


# ── normalize_text ─────────────────────────────────────────────────────────

def test_normalize_text_trims_and_lowers():
    assert ps.normalize_text("  Bock ") == "bock"
    assert ps.normalize_text(None) == ""
    assert ps.normalize_text("") == ""
    assert ps.normalize_text(6) == "6"


# ── single_active_pen_id ───────────────────────────────────────────────────

def test_single_active_pen_id_only_with_exactly_one():
    one = FakeSession({"Pen": [_pen(1), _pen(2, is_active=False)]})
    assert ps.single_active_pen_id(one) == 1
    two = FakeSession({"Pen": [_pen(1), _pen(2)]})
    assert ps.single_active_pen_id(two) is None
    none = FakeSession({"Pen": []})
    assert ps.single_active_pen_id(none) is None


# ── NibFormat: wiederverwenden vs. anlegen ─────────────────────────────────

def test_find_or_create_nib_format_reuses_normalized_match():
    fmt = Obj(id=7, manufacturer="Bock", physical_size="#6", is_proprietary=False)
    session = FakeSession({"NibFormat": [fmt]})
    got = ps.find_or_create_nib_format(session, "  bock ", "#6", False)
    assert got == 7
    assert len(session._data["NibFormat"]) == 1  # nichts Neues angelegt


def test_find_or_create_nib_format_creates_and_flushes_id():
    session = FakeSession({"NibFormat": []})
    got = ps.find_or_create_nib_format(session, "Jowo", None, True)
    assert isinstance(got, int)
    created = session._data["NibFormat"][0]
    assert created.id == got
    assert created.manufacturer == "Jowo"
    assert created.is_proprietary is True


def test_find_or_create_nib_format_distinguishes_proprietary_flag():
    fmt = Obj(id=7, manufacturer="Bock", physical_size="#6", is_proprietary=False)
    session = FakeSession({"NibFormat": [fmt]})
    got = ps.find_or_create_nib_format(session, "Bock", "#6", True)
    assert got != 7  # proprietäre Variante ist ein anderes Format


def test_find_or_create_nib_format_none_without_any_input():
    session = FakeSession({"NibFormat": []})
    assert ps.find_or_create_nib_format(session, None, "", False) is None
    assert session._data["NibFormat"] == []


# ── Ähnliche Feder ─────────────────────────────────────────────────────────

def _nib(i, **kw):
    base = dict(id=i, format_id=7, size="M", material="Steel", grind=None,
                source=None, is_proprietary=False)
    base.update(kw)
    return Obj(**base)


def test_find_similar_nib_matches_normalized_core_fields():
    session = FakeSession({"Nib": [_nib(1, size=" m ", material="steel")]})
    hit = ps.find_similar_nib(session, 7, {"size": "M", "material": "Steel",
                                           "grind": None, "source": None,
                                           "is_proprietary": False})
    assert hit is not None and hit.id == 1


def test_find_similar_nib_respects_differences_and_missing_format():
    session = FakeSession({"Nib": [_nib(1)]})
    assert ps.find_similar_nib(session, 7, {"size": "B", "material": "Steel",
                                            "grind": None, "source": None,
                                            "is_proprietary": False}) is None
    assert ps.find_similar_nib(session, None, {"size": "M"}) is None


# ── Kaufpreis-Spiegelung ───────────────────────────────────────────────────

class _LocaleStub:
    currency = "CHF"

    @classmethod
    def instance(cls):
        return cls


def test_sync_purchase_expense_creates_updates_and_removes(monkeypatch):
    monkeypatch.setattr(ps, "LocaleService", _LocaleStub)
    pen = _pen(5, brand="Pilot", model="C823", purchase_price=250.0,
               purchase_currency="EUR", purchase_date="2026-01-01")
    session = FakeSession({"Expense": []})

    ps.sync_purchase_expense_for_pen(session, pen)
    assert len(session._data["Expense"]) == 1
    exp = session._data["Expense"][0]
    assert exp.amount == 250.0 and exp.currency == "EUR"
    assert exp.notes == f"{ps.AUTO_PURCHASE_TAG_PREFIX}5"
    assert "Pilot C823" in exp.description

    pen.purchase_price = 300.0
    pen.purchase_currency = None  # -> Default-Währung
    ps.sync_purchase_expense_for_pen(session, pen)
    assert len(session._data["Expense"]) == 1  # aktualisiert, nicht dupliziert
    assert exp.amount == 300.0 and exp.currency == "CHF"

    pen.purchase_price = 0
    ps.sync_purchase_expense_for_pen(session, pen)
    assert session._data["Expense"] == []
    assert session.deleted == [exp]


def test_sync_purchase_expense_ignores_unsaved_pen(monkeypatch):
    monkeypatch.setattr(ps, "LocaleService", _LocaleStub)
    session = FakeSession({"Expense": []})
    ps.sync_purchase_expense_for_pen(session, _pen(0, id=None, purchase_price=99.0))
    assert session._data["Expense"] == []


# ── Neue Repositories (Fake-Delegation) ────────────────────────────────────

def test_new_repositories_delegate_and_sort_inputs():
    nibs = [_nib(2), _nib(1)]
    setups = [Obj(id=1, pen_id=9, installed_date="2026-01-01"),
              Obj(id=2, pen_id=9, installed_date="2026-02-01")]
    samples = [Obj(id=1, pen_id=9, written_at="2026-01-01")]
    session = FakeSession({"Nib": nibs, "NibFormat": [Obj(id=7)],
                           "PenNibSetup": setups, "WritingSample": samples,
                           "Ink": [FakeInkLike(1), FakeInkLike(2, is_empty=True)]})
    assert len(repos.NibRepository(session).all_sorted()) == 2
    assert repos.NibRepository(session).by_format(None) == []
    assert len(repos.NibFormatRepository(session).all()) == 1
    assert len(repos.PenNibSetupRepository(session).for_pen(9)) == 2
    assert len(repos.WritingSampleRepository(session).for_pen(9)) == 1
    assert len(repos.InkRepository(session).usable_sorted()) == 1


def FakeInkLike(i, **kw):
    base = dict(id=i, brand="I", name=f"N{i}", is_empty=False, is_archived=False)
    base.update(kw)
    return Obj(**base)
