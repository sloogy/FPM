"""Tests für die Rollen-/Themen-Konfiguration und das Tinten-Scoring."""
import pytest
from tests.conftest import FakeInk

from logic.role_config import (
    categorize_nib_size,
    score_ink_for_role,
    score_ink_for_theme,
    _score_ink_for_config,
    DEFAULT_ROLE_CONFIGS,
    DEFAULT_THEME_CONFIGS,
    NIB_SIZE_CATEGORIES,
    NIB_SIZE_INK_PREFS,
)


# ── categorize_nib_size ───────────────────────────────────────────
@pytest.mark.parametrize("raw,expected", [
    ("EF", "ef"), ("XXF", "ef"), ("F", "f"), ("M", "m"),
    ("B", "b"), ("BB", "b"), ("1.1", "b"), ("1.5 Stub", "stub"),
    ("Stub", "stub"), ("Cursive Italic", "stub"), ("Flex", "flex"),
    ("", None), ("   ", None), ("Wat", None),
])
def test_categorize_nib_size(raw, expected):
    assert categorize_nib_size(raw) == expected


def test_nib_categories_have_prefs():
    # Jede UI-Kategorie ausser 'm' (neutral) sollte Scoring-Präferenzen haben
    for code, _ in NIB_SIZE_CATEGORIES:
        assert code in NIB_SIZE_INK_PREFS


# ── score_ink_for_role: Nässe ─────────────────────────────────────
def test_fine_role_penalizes_dry_ink():
    dry = FakeInk(wetness_level=2)
    score, hints = score_ink_for_role("fine", dry, "converter", DEFAULT_ROLE_CONFIGS, nib_size="EF")
    assert score < 0
    assert any("trocken" in h.lower() or "dry" in h.lower() for h in hints)


def test_fine_role_rewards_wet_ink():
    wet = FakeInk(wetness_level=4)
    dry = FakeInk(wetness_level=2)
    s_wet, _ = score_ink_for_role("fine", wet, "converter", DEFAULT_ROLE_CONFIGS, nib_size="EF")
    s_dry, _ = score_ink_for_role("fine", dry, "converter", DEFAULT_ROLE_CONFIGS, nib_size="EF")
    assert s_wet > s_dry


# ── #2 Regression: keine Doppelbestrafung Nässe (Rolle + Nib) ─────
def test_no_double_wetness_penalty():
    """Bei konkreter Feder darf Nässe nur EINMAL bestraft werden."""
    dry = FakeInk(wetness_level=1)
    # fine-Rolle hat min_wetness 3, EF-Nib hat min_wetness 3 → früher -38, jetzt nur Nib
    score, hints = score_ink_for_role("fine", dry, "converter", DEFAULT_ROLE_CONFIGS, nib_size="EF")
    # Nur die Nib-Strafe (dry_penalty -18) sollte greifen, nicht zusätzlich score_miss
    dry_hints = [h for h in hints if "trocken" in h.lower() or "dry" in h.lower()]
    assert len(dry_hints) == 1, f"Erwartet genau 1 Trocken-Hinweis, bekam {dry_hints}"


# ── score_ink_for_role: Pigment/Shimmer ───────────────────────────
def test_collector_role_avoids_pigment():
    pig = FakeInk(is_pigment=True, cleaning_effort=2)
    score, hints = score_ink_for_role("collector", pig, "piston", DEFAULT_ROLE_CONFIGS, nib_size="M")
    # collector hat allow_pigment False → Strafe
    assert score < 0


def test_creative_role_rewards_sheen():
    sheen = FakeInk(sheen_level=4, has_sheen=True, usage_tags="creative,sheen_showcase")
    plain = FakeInk(sheen_level=0)
    s1, _ = score_ink_for_role("creative", sheen, "piston", DEFAULT_ROLE_CONFIGS, nib_size="B")
    s2, _ = score_ink_for_role("creative", plain, "piston", DEFAULT_ROLE_CONFIGS, nib_size="B")
    assert s1 > s2


# ── Tag-Matching ──────────────────────────────────────────────────
def test_tag_match_bonus():
    tagged = FakeInk(usage_tags="edc,work,document")
    untagged = FakeInk(usage_tags="creative")
    s1, _ = score_ink_for_role("edc", tagged, "converter", DEFAULT_ROLE_CONFIGS, nib_size="F")
    s2, _ = score_ink_for_role("edc", untagged, "converter", DEFAULT_ROLE_CONFIGS, nib_size="F")
    assert s1 > s2


# ── score_ink_for_theme ───────────────────────────────────────────
def test_theme_empty_returns_zero():
    score, hints = score_ink_for_theme(None, FakeInk(), "converter", DEFAULT_THEME_CONFIGS)
    assert score == 0 and hints == []


def test_theme_archive_rewards_waterproof():
    wp = FakeInk(is_waterproof=True, usage_tags="archive,document")
    score, hints = score_ink_for_theme("archive", wp, "piston", DEFAULT_THEME_CONFIGS, nib_size="M")
    assert score > 0


def test_theme_uses_same_core_as_role():
    """score_ink_for_theme und score_ink_for_role teilen _score_ink_for_config."""
    ink = FakeInk(wetness_level=4, usage_tags="creative")
    # Gleiche Config über beide Wege → gleiches Ergebnis
    cfg = DEFAULT_THEME_CONFIGS["creative"]
    direct, _ = _score_ink_for_config(cfg, ink, "piston", "B", "Kreativ")
    via_theme, _ = score_ink_for_theme("creative", ink, "piston", DEFAULT_THEME_CONFIGS, nib_size="B")
    assert direct == via_theme


# ── Konfigurationsintegrität ──────────────────────────────────────
def test_all_default_roles_have_required_keys():
    required = {"min_wetness", "max_wetness", "max_cleaning", "target_tags",
                "score_match", "score_miss", "preferred_nib_sizes"}
    for role, cfg in DEFAULT_ROLE_CONFIGS.items():
        missing = required - set(cfg.keys())
        assert not missing, f"Rolle {role} fehlen Schlüssel: {missing}"


def test_all_default_themes_have_required_keys():
    required = {"min_wetness", "max_wetness", "max_cleaning", "target_tags",
                "score_match", "score_miss"}
    for theme, cfg in DEFAULT_THEME_CONFIGS.items():
        missing = required - set(cfg.keys())
        assert not missing, f"Thema {theme} fehlen Schlüssel: {missing}"


def test_preferred_nib_sizes_are_valid_categories():
    valid = {c for c, _ in NIB_SIZE_CATEGORIES}
    for role, cfg in DEFAULT_ROLE_CONFIGS.items():
        for nib in cfg.get("preferred_nib_sizes", []):
            assert nib in valid, f"Rolle {role}: unbekannte Nib-Kategorie {nib!r}"


# ── v0.2.46 Merge: preferred_fill_systems wirken im Scoring (#3) ──
def test_preferred_fill_system_match_bonus():
    """Passendes Füllsystem soll Bonus geben, unpassendes Malus (gegenüber neutral)."""
    cfg = {
        "min_wetness": 1, "max_wetness": 5, "max_cleaning": 5,
        "allow_shimmer": None, "allow_pigment": None,
        "prefer_sheen": False, "prefer_shading": False,
        "target_tags": [], "preferred_nib_sizes": [],
        "preferred_fill_systems": ["piston", "converter"],
        "score_match": 16, "score_miss": -10,
    }
    from logic.role_config import _score_ink_for_config
    ink = FakeInk(wetness_level=3)
    s_match, h_match = _score_ink_for_config(cfg, ink, "piston", None, "TestRole")
    s_miss,  h_miss  = _score_ink_for_config(cfg, ink, "vac",    None, "TestRole")
    assert s_match > s_miss, f"Passendes Füllsystem ({s_match}) muss besser sein als unpassendes ({s_miss})"


def test_preferred_fill_system_empty_no_effect():
    """Ohne konfigurierte Füllsysteme darf das Füllsystem den Score nicht ändern."""
    cfg = {
        "min_wetness": 1, "max_wetness": 5, "max_cleaning": 5,
        "allow_shimmer": None, "allow_pigment": None,
        "prefer_sheen": False, "prefer_shading": False,
        "target_tags": [], "preferred_nib_sizes": [],
        "preferred_fill_systems": [],
        "score_match": 16, "score_miss": -10,
    }
    from logic.role_config import _score_ink_for_config
    ink = FakeInk(wetness_level=3)
    s_piston, _ = _score_ink_for_config(cfg, ink, "piston", None, "TestRole")
    s_vac,    _ = _score_ink_for_config(cfg, ink, "vac",    None, "TestRole")
    assert s_piston == s_vac, "Ohne preferred_fill_systems darf das Füllsystem nichts ändern"


def test_edc_default_has_fill_systems():
    """Regression: edc-Default soll Füllsysteme definiert haben (sonst wirkt #3 nie)."""
    assert DEFAULT_ROLE_CONFIGS["edc"]["preferred_fill_systems"]
