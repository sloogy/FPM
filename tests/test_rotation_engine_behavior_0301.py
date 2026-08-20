"""v0.3.01: Verhaltenstests für die Rotations-Engine (Enterprise-Audit P1).

Fokus auf die entscheidungsrelevanten reinen Pfade: Standzeit-Bonuskurve,
Farbfamilien-Penalty (inkl. Fixpaar-Ausnahme), CSV-/Farb-Helfer,
Rollenheuristik sowie der Sicherheitsfilter von ``_apply_randomness``
(harte Blocker fliegen auch im Zufallsmodus raus, feste Paarungen 💍
bleiben – Override-Prinzip; 0 %/100 %-Mischung des Scores).
"""
from __future__ import annotations

import pytest

# Importiert zuerst tests.conftest: aktiviert in der Sandbox den
# SQLAlchemy-Stub, bevor database/logic geladen werden (in der echten
# CI mit installiertem SQLAlchemy ist der Stub inaktiv, Import harmlos).
from tests.conftest import FakeInk as _StubHook  # noqa: F401

from logic import rotation_engine as rot_mod
from logic.rotation_engine import RotationEngine


class FakeInk:
    def __init__(self, **kw):
        self.color_family = kw.get("color_family", "blue")
        self.color_hex = kw.get("color_hex", "#0000ff")
        for k, v in kw.items():
            setattr(self, k, v)


@pytest.fixture
def engine():
    return RotationEngine()


# ── Reine Helfer ───────────────────────────────────────────────────────────

def test_split_csv_normalizes_and_deduplicates():
    assert rot_mod._split_csv(" Blau, grün ,BLAU,,") == {"blau", "grün"}
    assert rot_mod._split_csv(None) == set()
    assert rot_mod._split_csv(["A", " b "]) == {"a", "b"}


def test_color_distance_identity_and_symmetry():
    assert rot_mod._color_distance("#112233", "#112233") == 0
    d1 = rot_mod._color_distance("#000000", "#ffffff")
    d2 = rot_mod._color_distance("#ffffff", "#000000")
    assert d1 == d2 > 0


def test_ink_last_used_bonus_is_monotonic(engine):
    days = [0, 13, 14, 29, 30, 89, 90, 179, 180, 998, 999]
    boni = [engine._ink_last_used_bonus(d) for d in days]
    assert boni == sorted(boni), "Bonus muss mit Standzeit monoton wachsen"
    assert engine._ink_last_used_bonus(999) == 90   # nie benutzt = Maximum
    assert engine._ink_last_used_bonus(0) == 0


def test_infer_pen_role_priority():
    class P:
        def __init__(self, **kw):
            for k, v in kw.items():
                setattr(self, k, v)
    # 1) explizite Nicht-Writer-Rolle schlägt alles
    assert rot_mod._infer_pen_role(P(rotation_role="collector", tags="problem")) == "collector"
    # explizites "writer" darf von Tags übersteuert werden
    assert rot_mod._infer_pen_role(P(rotation_role="writer", tags="problem")) == "problem"
    # 2) Tags (als CSV-String pen.tags, nicht tags_list)
    assert rot_mod._infer_pen_role(P(tags="grail")) == "collector"
    assert rot_mod._infer_pen_role(P(tags="vintage")) == "vintage"
    # 3) Pflichtstatus
    assert rot_mod._infer_pen_role(P(must_include_in_rotation=True)) == "must"
    # 5) generischer Default ohne Feder/Tags
    assert rot_mod._infer_pen_role(P()) == "writer"


# ── Farbfamilien-Penalty ───────────────────────────────────────────────────

def test_color_family_penalty_active_vs_new(engine):
    active = {"blue"}
    malus, reason = engine._color_family_penalty(FakeInk(color_family="blue"), active, False)
    assert malus == -18 and reason
    bonus, reason2 = engine._color_family_penalty(FakeInk(color_family="red"), active, False)
    assert bonus == 14 and reason2


def test_color_family_penalty_fixed_pairing_is_exempt(engine):
    malus, reason = engine._color_family_penalty(FakeInk(color_family="blue"), {"blue"}, True)
    assert (malus, reason) == (0, "")


def test_color_family_penalty_without_family_is_neutral(engine):
    assert engine._color_family_penalty(FakeInk(color_family=None), {"blue"}, False) == (0, "")


# ── Randomness: Sicherheitsfilter & Mischung ───────────────────────────────

def _combo(score=100, *, is_fixed=False, has_blocked=False, auto_action="allow", name="c"):
    return {
        "score": score,
        "is_fixed": is_fixed,
        "has_blocked": has_blocked,
        "auto_action": auto_action,
        "hints": [],
        "rule_warnings": [],
        "name": name,
    }


def test_apply_randomness_filters_dangerous_combos(engine):
    combos = [
        _combo(name="ok"),
        _combo(name="blockiert", has_blocked=True),
        _combo(name="reject", auto_action="reject"),
        _combo(name="fix_blockiert", has_blocked=True, is_fixed=True),  # 💍 Override
    ]
    out = engine._apply_randomness(combos, 50)
    names = {c["name"] for c in out}
    assert names == {"ok", "fix_blockiert"}
    for c in out:
        assert c["random_mode"] is True
        assert c["random_percent"] == 50
        assert isinstance(c["random_delta"], int)
        assert c["hints"], "Zufallsmodus-Hinweis muss gesetzt sein"


def test_apply_randomness_zero_percent_keeps_deterministic_score(engine):
    combos = [_combo(score=87)]
    out = engine._apply_randomness(combos, 0)
    assert out[0]["score"] == 87
    assert out[0]["random_delta"] == 0


def test_apply_randomness_hundred_percent_ignores_deterministic_score(engine):
    # Bei 100 % besteht der Score nur aus Jitter (−140..140) – unabhängig vom
    # deterministischen Ausgangswert. Wir prüfen die Grenzen über viele Läufe.
    for _ in range(25):
        out = engine._apply_randomness([_combo(score=10_000)], 100)
        assert -140 <= out[0]["score"] <= 140


def test_apply_randomness_does_not_mutate_input(engine):
    original = _combo(score=55)
    engine._apply_randomness([original], 30)
    assert original["score"] == 55
    assert "random_mode" not in original


def test_rotation_randomness_percent_clamps_and_parses(engine, monkeypatch):
    values = {}
    monkeypatch.setattr(
        rot_mod.AppSettings, "get",
        staticmethod(lambda session, key, default=None: values.get(key, default)),
    )
    for raw, expected in [("0", 0), ("100", 100), ("250", 100), ("-5", 0),
                          ("37,5", 37), ("kaputt", 0), (None, 0)]:
        values["rotation_randomness_percent"] = raw
        assert engine._rotation_randomness_percent(object()) == expected


# ── Kontext: aktive Tinten/Familien (Fake-Session) ─────────────────────────

class _Load:
    def __init__(self, ink):
        self.ink = ink
        self.ink_id = getattr(ink, "id", 0)


class _Pen:
    def __init__(self, pen_id, ink=None, fixed=None, blocked=False):
        self.id = pen_id
        self.brand = "B"; self.model = f"M{pen_id}"
        self.is_active = True
        self.rotation_blocked = blocked
        self.availability_status = "available"
        self.current_ink_load = _Load(ink) if ink else None
        self.fixed_ink_id = fixed
        self.tags_list = []


class _Q:
    def __init__(self, items): self._items = items
    def filter_by(self, **kw):
        return _Q([i for i in self._items
                   if all(getattr(i, k, None) == v for k, v in kw.items())])
    def all(self): return list(self._items)


class _Session:
    def __init__(self, pens, inks=None):
        self._pens = pens
        # Ink-Register aus explizit übergebenen Inks plus den in Loads genutzten.
        reg = {getattr(i, "id", None): i for i in (inks or [])}
        for p in pens:
            load = getattr(p, "current_ink_load", None)
            if load is not None and getattr(load, "ink", None) is not None:
                reg[getattr(load.ink, "id", None)] = load.ink
        self._inks = reg
    def query(self, model): return _Q(self._pens)
    def get(self, model, oid): return self._inks.get(oid)


def test_active_rotation_context_collects_inks_and_families(engine):
    blue = FakeInk(id=1, color_family="blue")
    red = FakeInk(id=2, color_family="red")
    pens = [_Pen(1, ink=blue), _Pen(2, ink=red), _Pen(3)]
    active_ids, families, _pairs = engine._active_rotation_context(_Session(pens))
    assert active_ids == {1, 2}
    assert families == {"blue", "red"}


def test_active_rotation_context_excludes_requested_pen(engine):
    blue = FakeInk(id=1, color_family="blue")
    pens = [_Pen(1, ink=blue), _Pen(2, ink=FakeInk(id=2, color_family="red"))]
    active_ids, families, _ = engine._active_rotation_context(
        _Session(pens), exclude_pen_id=1
    )
    assert 1 not in active_ids
    assert "blue" not in families
