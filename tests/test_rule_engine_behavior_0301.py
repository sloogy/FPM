"""v0.3.01: Verhaltenstests für die Regel-Engine (Enterprise-Audit P1).

Deckt die harten Kernpfade ab: alle sechs Bedingungstypen von
``_evaluate``, Warnstufen-Malus vs. explizites ``score_delta``,
Blocking-Verdrängung, Bonus-Logik (Popularität, Pflicht, feste Paarung),
Score-Clamp sowie ``max_days_for`` mit Tinten-Vorrang und
Settings-Kaskade. Läuft mit Fake-Session – in der CI gegen echtes
SQLAlchemy, in der Sandbox über den conftest-Stub.
"""
from __future__ import annotations

import pytest

# Importiert zuerst tests.conftest: aktiviert in der Sandbox den
# SQLAlchemy-Stub, bevor database/logic geladen werden (in der echten
# CI mit installiertem SQLAlchemy ist der Stub inaktiv, Import harmlos).
from tests.conftest import FakeInk as _StubHook  # noqa: F401

from logic import rule_engine as re_mod
from logic.rule_engine import RuleEngine, RuleViolation


# ── Fakes ───────────────────────────────────────────────────────────────────

class FakeNib:
    """Minimaler Feder-Stub – die Engine liest pen.nib.size / .grind etc."""
    def __init__(self, size=None, grind=None, **kw):
        self.size = size
        self.grind = grind
        self.manufacturer = kw.get("manufacturer", "")
        self.material = kw.get("material", "")
        self.is_flexible = kw.get("is_flexible", False)
        self.stiffness_level = kw.get("stiffness_level", 4)


class FakePen:
    def __init__(self, **kw):
        self.id = kw.get("id", 1)
        self.brand = kw.get("brand", "Test")
        self.model = kw.get("model", "Pen")
        self.fill_system = kw.get("fill_system", "converter")
        self.tags_list = kw.get("tags_list", [])
        self.popularity_rating = kw.get("popularity_rating", 3)
        self.must_include_in_rotation = kw.get("must_include_in_rotation", False)
        self.fixed_ink_id = kw.get("fixed_ink_id", None)
        # Verschachtelte Feder wie im echten Modell (pen.nib), kein aktives Setup.
        self.active_nib_setup = None
        if "nib_size" in kw or "nib_grind" in kw:
            self.nib = FakeNib(size=kw.get("nib_size"), grind=kw.get("nib_grind"))
        else:
            self.nib = kw.get("nib", None)


class FakeInk:
    def __init__(self, **kw):
        self.id = kw.get("id", 10)
        self.has_shimmer = kw.get("has_shimmer", False)
        self.has_sheen = kw.get("has_sheen", False)
        self.has_shading = kw.get("has_shading", False)
        self.is_pigment = kw.get("is_pigment", False)
        self.is_waterproof = kw.get("is_waterproof", False)
        self.wetness_level = kw.get("wetness_level", 3)
        self.cleaning_effort = kw.get("cleaning_effort", 3)
        self.max_days_in_pen = kw.get("max_days_in_pen", None)


class FakeRule:
    _next_id = 1
    def __init__(self, condition_type, condition_data="{}", *, warn_level="warning",
                 rule_type="soft", score_delta=None, auto_action="warn",
                 rule_group="rotation", name=None):
        self.id = FakeRule._next_id; FakeRule._next_id += 1
        self.name = name or f"R{self.id}"
        self.description = ""
        self.condition_type = condition_type
        self.condition_data = condition_data
        self.warn_level = warn_level
        self.rule_type = rule_type
        self.score_delta = score_delta
        self.auto_action = auto_action
        self.rule_group = rule_group
        self.is_active = True


class FakeQuery:
    def __init__(self, rules):
        self._rules = rules
    def filter_by(self, **kw):
        return FakeQuery([r for r in self._rules
                          if all(getattr(r, k, None) == v for k, v in kw.items())])
    def all(self):
        return list(self._rules)


class FakeSession:
    def __init__(self, rules):
        self._rules = rules
    def query(self, model):
        return FakeQuery(self._rules)
    def close(self):
        pass


@pytest.fixture
def enable_rules(monkeypatch):
    monkeypatch.setattr(re_mod.AutoModeService, "rules_enabled",
                        staticmethod(lambda session: True))
    monkeypatch.setattr(re_mod.AutoModeService, "group_enabled",
                        staticmethod(lambda session, group: True))


# ── _evaluate: alle Bedingungstypen ────────────────────────────────────────

def test_evaluate_fill_system_ink_prop_triggers_exactly():
    eng = RuleEngine()
    rule = FakeRule("fill_system_ink_prop",
                    '{"fill_system": "vac", "prop": "has_shimmer", "value": true}',
                    warn_level="critical", rule_type="hard")
    vac_shimmer = eng._evaluate(rule, FakePen(fill_system="vac"), FakeInk(has_shimmer=True))
    assert isinstance(vac_shimmer, RuleViolation)
    assert vac_shimmer.warn_level == "critical"
    assert eng._evaluate(rule, FakePen(fill_system="piston"), FakeInk(has_shimmer=True)) is None
    assert eng._evaluate(rule, FakePen(fill_system="vac"), FakeInk(has_shimmer=False)) is None


def test_evaluate_nib_size_wetness_uses_min_threshold():
    eng = RuleEngine()
    rule = FakeRule("nib_size_wetness", '{"nib_size": "EF", "wetness_min": 4}')
    dry = FakeInk(wetness_level=2)
    wet = FakeInk(wetness_level=4)
    ef_pen = FakePen(nib_size="ef")  # Groß-/Kleinschreibung egal
    assert eng._evaluate(rule, ef_pen, dry) is not None
    assert eng._evaluate(rule, ef_pen, wet) is None
    assert eng._evaluate(rule, FakePen(nib_size="M"), dry) is None
    assert eng._evaluate(rule, FakePen(nib_size=None), dry) is None


def test_evaluate_ink_prop_and_pen_tag_variants():
    eng = RuleEngine()
    pigment_rule = FakeRule("ink_prop_warning", '{"prop": "is_pigment", "value": true}')
    assert eng._evaluate(pigment_rule, FakePen(), FakeInk(is_pigment=True)) is not None
    assert eng._evaluate(pigment_rule, FakePen(), FakeInk()) is None

    grail_rule = FakeRule("pen_tag_ink_prop",
                          '{"tag": "Grail", "prop": "has_shimmer", "value": true}')
    grail_pen = FakePen(tags_list=["  GRAIL  ", "vintage"])  # normalisiert
    assert eng._evaluate(grail_rule, grail_pen, FakeInk(has_shimmer=True)) is not None
    assert eng._evaluate(grail_rule, FakePen(tags_list=["edc"]), FakeInk(has_shimmer=True)) is None

    sheen_rule = FakeRule("pen_tag_sheen_cleaning", '{"tag": "grail", "cleaning_min": 4}')
    assert eng._evaluate(sheen_rule, grail_pen, FakeInk(has_sheen=True, cleaning_effort=5)) is not None
    assert eng._evaluate(sheen_rule, grail_pen, FakeInk(has_sheen=True, cleaning_effort=3)) is None
    assert eng._evaluate(sheen_rule, grail_pen, FakeInk(has_sheen=False, cleaning_effort=5)) is None


def test_evaluate_grind_prefers_prop_triggers_when_prop_missing():
    eng = RuleEngine()
    rule = FakeRule("nib_grind_prefers_ink_prop",
                    '{"grinds": ["stub", "italic"], "props": ["has_sheen", "has_shading"]}')
    stub_pen = FakePen(nib_grind="Stub 1.1")
    assert eng._evaluate(rule, stub_pen, FakeInk()) is not None          # kein Prop → Hinweis
    assert eng._evaluate(rule, stub_pen, FakeInk(has_sheen=True)) is None
    assert eng._evaluate(rule, FakePen(nib_grind=None), FakeInk()) is None


def test_evaluate_broken_condition_json_never_raises():
    eng = RuleEngine()
    rule = FakeRule("fill_system_ink_prop", '{kaputt')
    assert eng._evaluate(rule, FakePen(fill_system="vac"), FakeInk(has_shimmer=True)) is None


# ── check(): Aktivierung, Gruppen, Session-Hoheit ──────────────────────────

def test_check_collects_only_matching_active_rules(enable_rules):
    eng = RuleEngine()
    r_hit = FakeRule("ink_prop_warning", '{"prop": "has_shimmer", "value": true}')
    r_miss = FakeRule("ink_prop_warning", '{"prop": "is_pigment", "value": true}')
    r_off = FakeRule("ink_prop_warning", '{"prop": "has_shimmer", "value": true}')
    r_off.is_active = False
    session = FakeSession([r_hit, r_miss, r_off])
    violations = eng.check(FakePen(), FakeInk(has_shimmer=True), session=session)
    assert [v.rule_id for v in violations] == [r_hit.id]


def test_check_returns_empty_when_rules_disabled(monkeypatch):
    monkeypatch.setattr(re_mod.AutoModeService, "rules_enabled",
                        staticmethod(lambda session: False))
    eng = RuleEngine()
    session = FakeSession([FakeRule("ink_prop_warning", '{"prop": "has_shimmer", "value": true}')])
    assert eng.check(FakePen(), FakeInk(has_shimmer=True), session=session) == []


# ── score(): Malus, Delta, Boni, Blocking, Clamp ───────────────────────────

def _violation(warn_level="warning", score_delta=None, rule_type="soft"):
    return RuleViolation(1, "R", "", warn_level, rule_type, True,
                         "rotation", "warn", score_delta)


def test_score_uses_penalty_table_or_explicit_delta():
    eng = RuleEngine()
    pen, ink = FakePen(popularity_rating=3), FakeInk()
    base = eng.score(pen, ink, violations=[])
    warn = eng.score(pen, ink, violations=[_violation("warning")])
    assert warn == base - re_mod.PENALTY["warning"]
    delta = eng.score(pen, ink, violations=[_violation("warning", score_delta=-5)])
    assert delta == base - 5  # explizites Delta hat Vorrang vor Warnstufen-Malus


def test_score_bonuses_popularity_must_include_fixed_pairing():
    eng = RuleEngine()
    ink = FakeInk(id=42)
    base = eng.score(FakePen(popularity_rating=3), ink, violations=[])
    assert eng.score(FakePen(popularity_rating=5), ink, violations=[]) == base + 4
    assert eng.score(FakePen(must_include_in_rotation=True), ink, violations=[]) == base + 18
    assert eng.score(FakePen(fixed_ink_id=42), ink, violations=[]) == base + 40


def test_score_blocking_violation_displaces_suggestion():
    eng = RuleEngine()
    pen, ink = FakePen(), FakeInk()
    blocked = eng.score(pen, ink, violations=[
        _violation("blocked", rule_type="hard"),
    ])
    assert blocked <= eng.score(pen, ink, violations=[]) - 120 + 5  # Malus + Blocking


def test_score_is_clamped_to_range():
    eng = RuleEngine()
    many = [_violation("critical") for _ in range(20)]
    assert eng.score(FakePen(), FakeInk(), violations=many) == -100
    boni = FakePen(popularity_rating=5, must_include_in_rotation=True, fixed_ink_id=42)
    assert eng.score(boni, FakeInk(id=42, has_sheen=True), violations=[]) == 150


def test_has_blocking_violation_detects_hard_and_blocked():
    eng = RuleEngine()
    assert eng.has_blocking_violation([_violation("warning")]) is False
    assert eng.has_blocking_violation([_violation("blocked")]) is True
    assert eng.has_blocking_violation(None) is False


# ── max_days_for(): Tinten-Vorrang und Settings-Kaskade ────────────────────

@pytest.fixture
def settings(monkeypatch):
    values = {
        "cleaning_days_normal": "28",
        "cleaning_days_shimmer": "14",
        "cleaning_days_pigment": "10",
        "cleaning_days_grail": "21",
    }
    monkeypatch.setattr(
        re_mod.AppSettings, "get",
        staticmethod(lambda session, key, default=None: values.get(key, default)),
    )
    return values


def test_max_days_ink_value_has_priority(settings):
    eng = RuleEngine()
    ink = FakeInk(max_days_in_pen=7, has_shimmer=True)
    assert eng.max_days_for(FakePen(), ink, session=object()) == 7


def test_max_days_cascade_takes_minimum(settings):
    eng = RuleEngine()
    session = object()
    assert eng.max_days_for(FakePen(), FakeInk(), session=session) == 28
    assert eng.max_days_for(FakePen(), FakeInk(has_shimmer=True), session=session) == 14
    assert eng.max_days_for(FakePen(), FakeInk(is_pigment=True), session=session) == 10
    assert eng.max_days_for(FakePen(), FakeInk(is_waterproof=True), session=session) == 10
    grail = FakePen(tags_list=["Grail"])
    assert eng.max_days_for(grail, FakeInk(), session=session) == 21
    # Grail + Shimmer → das strengere Limit gewinnt
    assert eng.max_days_for(grail, FakeInk(has_shimmer=True), session=session) == 14
