"""v0.2.80 (Merge): Prozent-Zufall, Paar-Reroll, UI-Verdrahtung.

Die Engine-Zufallslogik wird REAL getestet: database/event_bus werden vor dem
Import gestubbt, die Engine-Instanz ohne __init__ erzeugt (kein Qt nötig).
Getestet werden ``_apply_randomness`` (Sicherheitsfilter, Jitter, Metadaten)
und das Zusammenspiel mit der echten ``_build_suggestion_set``-Auswahl
(strukturelle 💍/⭐-Garantien). Der DB-gebundene ``get_suggestions``-Pfad wird
statisch geprüft (Sandbox ohne SQLAlchemy/PySide6).
"""
import importlib.util
import json
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_rotation_engine_with_stubs():
    """Importiert logic.rotation_engine mit gestubbtem DB-/Qt-Unterbau."""
    saved = {k: sys.modules.get(k) for k in (
        "database", "database.db", "database.models", "logic.event_bus",
    )}
    db_pkg = types.ModuleType("database")
    db_db = types.ModuleType("database.db")
    db_db.get_session = lambda: None
    db_models = types.ModuleType("database.models")
    for cls in ("Pen", "Ink", "InkLoad", "Rule", "OverrideLog"):
        setattr(db_models, cls, type(cls, (), {}))

    class _FakeAppSettings:
        @classmethod
        def get(cls, session, key, default=None):
            return default

    db_models.AppSettings = _FakeAppSettings
    bus = types.ModuleType("logic.event_bus")

    class _FakeBus:
        @classmethod
        def instance(cls):
            return cls()

        def __getattr__(self, name):
            return types.SimpleNamespace(connect=lambda *a, **k: None,
                                         emit=lambda *a, **k: None)

    bus.AppEventBus = _FakeBus
    sys.modules["database"] = db_pkg
    sys.modules["database.db"] = db_db
    sys.modules["database.models"] = db_models
    sys.modules["logic.event_bus"] = bus
    sys.modules.pop("logic.rotation_engine", None)
    try:
        spec = importlib.util.spec_from_file_location(
            "logic.rotation_engine", ROOT / "logic" / "rotation_engine.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
        sys.modules.pop("logic.rotation_engine", None)


def _combo(pen_id, ink_id, *, score=0, blocked=False, fixed=False, must=False,
           auto_action=None, hex_="#123456"):
    return {
        "pen_id": pen_id, "ink_id": ink_id,
        "pen_name": f"P{pen_id}", "ink_name": f"I{ink_id}",
        "color_hex": hex_, "color_family_norm": "blue",
        "score": score, "has_blocked": blocked,
        "is_fixed": fixed, "is_must": must,
        "auto_action": auto_action,
        "hints": [], "rule_warnings": [], "warnings": "",
        "random_delta": 0,
    }


def _engine_instance(mod):
    return object.__new__(mod.RotationEngine)


# ── _apply_randomness: reale Methode ─────────────────────────────────
def test_randomness_excludes_pen_damaging_and_rejected_combos():
    mod = _load_rotation_engine_with_stubs()
    eng = _engine_instance(mod)
    combos = [
        _combo(1, 10, blocked=True),                 # schädlich → tabu
        _combo(1, 11),
        _combo(2, 12, auto_action="reject"),         # Auto-Reject → tabu
        _combo(3, 13, blocked=True, fixed=True),     # 💍 Override bleibt
    ]
    out = eng._apply_randomness(combos, 100)
    keys = {(c["pen_id"], c["ink_id"]) for c in out}
    assert (1, 10) not in keys
    assert (2, 12) not in keys
    assert (1, 11) in keys
    assert (3, 13) in keys  # feste Paarung überlebt den Filter


def test_randomness_sets_metadata_and_hint_with_pct():
    mod = _load_rotation_engine_with_stubs()
    eng = _engine_instance(mod)
    out = eng._apply_randomness([_combo(1, 11, score=50)], 75)
    c = out[0]
    assert c["random_mode"] is True
    assert c["random_percent"] == 75
    assert c["score"] == 50 + c["random_delta"]
    assert any("75" in str(h) for h in c["hints"])
    assert c["warnings"]  # Tooltip-String wurde neu aufgebaut


def test_randomness_zero_percent_never_called_but_full_random_varies():
    mod = _load_rotation_engine_with_stubs()
    eng = _engine_instance(mod)
    combos = [_combo(1, ink, score=0) for ink in range(10, 30)]
    winners = set()
    for _ in range(15):
        jittered = eng._apply_randomness([dict(c) for c in combos], 100)
        picked = eng._build_suggestion_set(jittered, 1, [])
        winners.add(picked[0]["ink_id"])
    assert len(winners) >= 3  # würfelt wirklich statt immer Top-Score


def test_full_random_keeps_fixed_pairing_structurally():
    mod = _load_rotation_engine_with_stubs()
    eng = _engine_instance(mod)
    # Füller 1 ist mit Tinte 10 verheiratet; Jitter darf das nicht kippen.
    for _ in range(10):
        combos = [
            _combo(1, 10, fixed=True),
            _combo(1, 11),
            _combo(1, 12),
        ]
        jittered = eng._apply_randomness(combos, 100)
        picked = eng._build_suggestion_set(jittered, 1, [])
        assert picked and picked[0]["ink_id"] == 10 and picked[0]["is_fixed"]


def test_full_random_prefers_must_pen_for_slots():
    mod = _load_rotation_engine_with_stubs()
    eng = _engine_instance(mod)
    for _ in range(10):
        combos = [
            _combo(1, 10),
            _combo(2, 11, must=True),
            _combo(3, 12),
        ]
        jittered = eng._apply_randomness(combos, 100)
        picked = eng._build_suggestion_set(jittered, 1, [])
        assert picked and picked[0]["pen_id"] == 2  # ⭐ zuerst in die Slots


def test_full_random_unique_pens_inks_and_slot_cap():
    mod = _load_rotation_engine_with_stubs()
    eng = _engine_instance(mod)
    combos = [_combo(p, i) for p in (1, 2, 3, 4) for i in (10, 11, 12, 13)]
    picked = eng._build_suggestion_set(eng._apply_randomness(combos, 100), 3, [])
    assert len(picked) == 3
    assert len({c["pen_id"] for c in picked}) == 3
    assert len({c["ink_id"] for c in picked}) == 3


def test_randomness_percent_parser_is_robust():
    mod = _load_rotation_engine_with_stubs()
    eng = _engine_instance(mod)

    class _S:
        def __init__(self, v): self.v = v

    def _get(session, key, default=None):
        return session.v

    mod.AppSettings.get = classmethod(lambda cls, session, key, default=None: session.v)
    assert eng._rotation_randomness_percent(_S("35")) == 35
    assert eng._rotation_randomness_percent(_S("77,5")) == 77
    assert eng._rotation_randomness_percent(_S("150")) == 100
    assert eng._rotation_randomness_percent(_S("-3")) == 0
    assert eng._rotation_randomness_percent(_S("unsinn")) == 0
    assert eng._rotation_randomness_percent(_S(None)) == 0


# ── Reroll & Setting-Verdrahtung: statisch (DB-Pfad, Sandbox-Grenze) ──
def _src(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def test_engine_get_suggestions_supports_pair_avoid_and_percent_setting():
    src = _src("logic/rotation_engine.py")
    assert "avoid_pairs: set[tuple[int, int]] | None = None" in src
    assert 'AppSettings.get(session, "rotation_randomness_percent"' in src
    assert "_apply_randomness" in src
    assert '"has_blocked": bool(has_blocking_rule)' in src
    # Reroll-Fallback: leerer Pool → volle Runde statt kein Vorschlag
    assert "repeat_round" in src and "respect_avoid=False" in src
    # Paar-Sperre, feste Paarung ausgenommen
    assert "(pen.id, ink.id) in avoid and pen.fixed_ink_id != ink.id" in src
    # Alter Binär-Zufallspfad ist vollständig entfernt
    assert "_build_random_suggestion_set" not in src
    assert "rotation_random_mode" not in src


def test_rotation_widget_wires_pair_reroll_memory():
    src = _src("ui/rotation_widget.py")
    assert "self._avoid_pairs" in src
    assert "avoid_pairs=self._avoid_pairs" in src
    assert '_avoid_pairs.update((s["pen_id"], s["ink_id"])' in src
    assert "setWordWrap(False)" in src


def test_rotation_widget_compact_warning_column():
    src = _src("ui/rotation_widget.py")
    assert "rule_warnings" in src and "hint_parts[:2]" in src
    assert 't("rotation.more_hints", n=hidden)' in src
    # Tooltip mehrzeilig statt |-Riesenstring
    assert 'warn_item.setToolTip("\\n".join(full_lines)' in src


def test_settings_page_exposes_percent_and_duplicate_options():
    src = _src("ui/settings_widget.py")
    assert "_build_rotation_page" in src
    assert "rotation_random_spin" in src and "rotation_duplicates_cb" in src
    assert "setRange(0, 100)" in src
    assert "AppSettings.set(session, 'rotation_randomness_percent'" in src
    assert "AppSettings.set(session, 'rotation_allow_active_ink_duplicates'" in src
    assert "AppSettings.get(session, 'rotation_randomness_percent', '0')" in src
    assert "settings.rotation_reroll_note" in src
    assert "rotation_random_mode" not in src


def test_db_seeds_percent_setting_not_legacy_toggle():
    src = _src("database/db.py")
    assert '"rotation_randomness_percent": "0"' in src
    assert "rotation_random_mode" not in src


def test_dashboard_declutter_markers():
    src = _src("ui/dashboard_widget.py")
    # 4 Karten statt 7, Kompaktzeile vorhanden
    assert "_card_pens" not in src and "_card_service" not in src and "_card_archived" not in src
    assert "_inventory_line" in src
    assert "dashboard.inventory_line" in src
    # Timer nur fällig/bald fällig, gekürzte Listen, kompakte Höhen (Merge aus B)
    assert '0.8 * r["max"]' in src
    assert ".limit(8)" in src and "limit=6," in src
    assert "setMaximumHeight(150)" in src


def test_rules_page_gets_overview_level_filter_and_i18n_labels():
    src = _src("ui/rules_widget.py")
    assert "rules.overview_explain" in src
    assert "rules.list_explainer" not in src  # ersetzt, nicht doppelt
    assert "level_filter" in src and 'rule.warn_level or "") != level' in src
    assert "_warn_level_label" in src and "_rule_type_label" in src
    # i18n-Leak behoben:
    assert '"Nein (Gruppe aus)"' not in src
    assert "rules.effective_no_group_off" in src


def test_new_i18n_keys_exist_in_all_languages():
    keys = [
        ("rotation", "hint_repeat_round"),
        ("rotation", "hint_random_mode"),
        ("rotation", "random_mode_active"),
        ("rotation", "more_hints"),
        ("dashboard", "inventory_line"),
        ("dashboard", "timer_title_counts"),
        ("dashboard", "lock_title_counts"),
        ("settings", "rotation_page_title"),
        ("settings", "rotation_random_label"),
        ("settings", "rotation_random_note"),
        ("settings", "rotation_allow_duplicates"),
        ("settings", "rotation_reroll_note"),
        ("settings", "rotation_save"),
        ("rules", "overview_explain"),
        ("rules", "level_filter_all"),
        ("rules", "effective_no_group_off"),
        ("rules", "type_hard"),
        ("rules", "type_soft"),
    ]
    for lang in ("de", "en", "fr"):
        data = json.loads((ROOT / "i18n" / f"{lang}.json").read_text(encoding="utf-8"))
        for path in keys:
            node = data
            for part in path:
                assert part in node, f"{lang}: {'.'.join(path)} fehlt"
                node = node[part]
            assert isinstance(node, str) and node.strip()
        # {pct}-Parameter in beiden Zufalls-Texten vorhanden
        assert "{pct}" in data["rotation"]["hint_random_mode"]
        assert "{pct}" in data["rotation"]["random_mode_active"]
