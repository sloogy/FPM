from datetime import datetime
from types import SimpleNamespace

from logic.writing_sample_service import (
    build_binder_tree,
    evaluate_sample,
    flatten_sample_ids,
    sample_quality_score,
    suggested_sample_title,
)


def obj(**kw):
    return SimpleNamespace(**kw)


def sample(**kw):
    base = dict(
        id=1,
        title="Test",
        sample_type="regular",
        pen_id=1,
        ink_id=1,
        paper_id=1,
        written_at=datetime(2026, 7, 4),
        sample_text="The quick brown fox",
        image_path=None,
        dry_time_seconds=10,
        feathering_level=1,
        bleedthrough_level=1,
        shading_level=3,
        sheen_level=0,
        flow_level=3,
        feedback_level=3,
        overall_rating=3,
    )
    base.update(kw)
    return obj(**base)


def test_suggested_sample_title_uses_real_combination_labels():
    pen = obj(brand="Pilot", model="Custom 74")
    ink = obj(brand="Pilot", name="Tsuki-yo")
    paper = obj(brand="Midori", name="MD")

    assert suggested_sample_title(pen, ink, paper) == "Pilot Custom 74 · Pilot Tsuki-yo · Midori MD"


def test_evaluate_sample_flags_missing_links_and_bad_paper_behavior():
    s = sample(pen_id=None, ink_id=None, paper_id=None, sample_text=None, feathering_level=5, bleedthrough_level=4, dry_time_seconds=60, overall_rating=2)

    codes = {issue.code for issue in evaluate_sample(s)}

    assert {"missing_pen", "missing_ink", "missing_paper", "missing_evidence", "heavy_feathering", "heavy_bleedthrough", "slow_dry", "low_rating"}.issubset(codes)


def test_quality_score_rewards_good_evidence_and_penalizes_bleedthrough():
    good = sample(id=1, overall_rating=5, feathering_level=1, bleedthrough_level=1, sample_text="abc")
    bad = sample(id=2, overall_rating=2, feathering_level=5, bleedthrough_level=5, sample_text=None)

    assert sample_quality_score(good) > sample_quality_score(bad)


def test_binder_tree_groups_samples_scrivener_style():
    samples = [
        sample(id=1, title="Blue test", overall_rating=5),
        sample(id=2, title="Problem test", pen_id=2, ink_id=2, paper_id=None, feathering_level=5),
    ]
    pens = {1: obj(brand="Pilot", model="Custom 74"), 2: obj(brand="Asvine", model="V800")}
    inks = {1: obj(brand="Pilot", name="Tsuki-yo"), 2: obj(brand="Diamine", name="Skull & Roses")}
    papers = {1: obj(brand="Midori", name="MD")}

    root = build_binder_tree(samples, pens, inks, papers)

    assert [child.title for child in root.children] == ["Nach Füller", "Nach Tinte", "Nach Papier", "Highlights", "Prüfen"]
    ids = flatten_sample_ids(root)
    assert 1 in ids and 2 in ids
    highlights = next(child for child in root.children if child.title == "Highlights")
    review = next(child for child in root.children if child.title == "Prüfen")
    assert flatten_sample_ids(highlights) == [1]
    assert 2 in flatten_sample_ids(review)


def test_compare_samples_returns_winner_and_limits_to_four():
    from logic.writing_sample_service import compare_samples

    samples = [
        sample(id=1, title="Bad", overall_rating=2, feathering_level=5, bleedthrough_level=5),
        sample(id=2, title="Good", overall_rating=5, feathering_level=1, bleedthrough_level=1, dry_time_seconds=8),
        sample(id=3, title="Okay"),
        sample(id=4, title="Also okay"),
        sample(id=5, title="Too much"),
    ]
    pens = {1: obj(brand="Pilot", model="Custom 74")}
    inks = {1: obj(brand="Pilot", name="Tsuki-yo")}
    papers = {1: obj(brand="Midori", name="MD")}

    comparison = compare_samples(samples, pens, inks, papers)

    assert len(comparison.rows) == 4
    assert comparison.winner_id == 2
    assert "limited_to_four" in comparison.warnings
