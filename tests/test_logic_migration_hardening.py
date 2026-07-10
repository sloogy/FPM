import sqlite3
from types import SimpleNamespace as NS

from database.db import init_db, get_session, SCHEMA_VERSION
from database.models import AppSettings, PenNibSetup
from logic.enthusiast_lab_service import (
    apply_ink_consumption,
    build_sample_grid,
    color_gap_rows,
    compare_axis_options,
    ink_fill_status,
    restock_recommendations,
)
from logic.writing_sample_service import compare_samples


def _ink(**kw):
    base = dict(
        id=1,
        brand="Diamine",
        name="Chocolate",
        bottle_size_ml=30.0,
        remaining_ml=20.0,
        reorder_threshold_ml=5.0,
        is_empty=False,
        is_archived=False,
        color_family="brown",
        color_type="warm brown",
        notes="",
        character_notes="",
    )
    base.update(kw)
    return NS(**base)


def _sample(**kw):
    base = dict(
        id=1,
        title="Sample",
        pen_id=1,
        ink_id=1,
        paper_id=1,
        image_path=None,
        sample_text="abc",
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
    return NS(**base)


def test_legacy_059_writing_samples_are_migrated(tmp_path):
    db_path = tmp_path / "legacy_059.db"

    # Zuerst eine vollständige aktuelle DB anlegen, dann nur die beiden
    # abweichenden Tabellen aus der alternativen v0.2.59-Linie simulieren.
    # So testen wir genau den realen Merge-Pfad, ohne ein künstlich zu altes
    # Gesamtschema zu erfinden.
    init_db(db_path)

    con = sqlite3.connect(db_path)
    con.executescript(
        """
        DELETE FROM pen_nib_setups;
        INSERT INTO pens(id, brand, model, fill_system, is_active, availability_status,
                         rotation_blocked, created_at, updated_at, popularity_rating, must_include_in_rotation)
        VALUES (900, 'Pilot', 'Custom 74', 'converter', 1, 'available', 0,
                '2026-07-01 00:00:00', '2026-07-01 00:00:00', 3, 0);
        INSERT INTO inks(id, brand, name, is_empty, is_archived, sheen_level, feathering_level,
                         shading_level, flow_level, saturation_level, has_shading, has_sheen, has_shimmer,
                         is_pigment, is_waterproof, wetness_level, cleaning_effort, created_at, updated_at)
        VALUES (900, 'Pilot', 'Tsuki-yo', 0, 0, 0, 1, 3, 3, 3, 0, 0, 0,
                0, 0, 3, 3, '2026-07-01 00:00:00', '2026-07-01 00:00:00');
        INSERT INTO papers(id, brand, name, paper_type, shading_suitable, sheen_suitable,
                           feathering_level, bleedthrough_level, is_edc, pages_used, created_at)
        VALUES (900, 'Midori', 'MD', 'notebook', 1, 1, 1, 1, 0, 0, '2026-07-01 00:00:00');
        INSERT INTO nibs(id, manufacturer, size, is_proprietary, stiffness_level, feedback_level, is_flexible, created_at)
        VALUES (900, 'Pilot', 'F', 0, 3, 3, 0, '2026-07-01 00:00:00');
        DROP TABLE writing_samples;
        CREATE TABLE writing_samples(
            id INTEGER PRIMARY KEY,
            pen_id INTEGER,
            ink_id INTEGER,
            paper_id INTEGER,
            nib_desc VARCHAR(120),
            image_path TEXT,
            notes TEXT,
            created_at DATETIME
        );
        CREATE TABLE IF NOT EXISTS nib_change_events(
            id INTEGER PRIMARY KEY,
            pen_id INTEGER,
            nib_id INTEGER,
            nib_label VARCHAR(120),
            changed_date DATETIME,
            reason TEXT
        );
        INSERT INTO writing_samples(id, pen_id, ink_id, paper_id, nib_desc, image_path, notes, created_at)
        VALUES (1, 900, 900, 900, 'Pilot F leicht nass', '/tmp/sample.jpg', 'alte Probe', '2026-07-01 12:00:00');
        INSERT INTO nib_change_events(id, pen_id, nib_id, nib_label, changed_date, reason)
        VALUES (1, 900, 900, 'Pilot F', '2026-07-02 08:00:00', 'Testwechsel');
        UPDATE app_settings SET value='0.2.59' WHERE key='schema_version';
        """
    )
    con.commit()
    con.close()

    init_db(db_path)

    con = sqlite3.connect(db_path)
    cols = {row[1] for row in con.execute("PRAGMA table_info(writing_samples)")}
    assert {"title", "written_at", "overall_rating", "feedback_level", "updated_at"}.issubset(cols)
    row = con.execute("SELECT title, sample_type, written_at, overall_rating, notes FROM writing_samples WHERE id=1").fetchone()
    assert row[0] == "Pilot Custom 74 · Pilot Tsuki-yo · Midori MD"
    assert row[1] == "regular"
    assert row[2] == "2026-07-01 12:00:00"
    assert row[3] == 3
    assert "Legacy-Feder: Pilot F leicht nass" in row[4]
    con.close()

    session = get_session()
    try:
        assert AppSettings.get(session, "schema_version") == SCHEMA_VERSION
        setups = session.query(PenNibSetup).filter_by(pen_id=900, nib_id=900).all()
        assert len(setups) == 1
        assert setups[0].setup_label == "Pilot F"
        assert setups[0].install_reason == "Testwechsel"
    finally:
        session.close()


def test_compare_samples_does_not_pick_problem_as_winner_when_clean_alternative_exists():
    problem_high_score = _sample(id=1, title="Problem aber beliebt", overall_rating=5, feathering_level=4, bleedthrough_level=1, flow_level=5, feedback_level=5)
    clean_good = _sample(id=2, title="Sauber", overall_rating=4, feathering_level=1, bleedthrough_level=1, flow_level=3, feedback_level=3)

    comparison = compare_samples([problem_high_score, clean_good])

    assert comparison.rows[0].verdict == "problem"
    assert comparison.winner_id == 2


def test_empty_inks_do_not_cover_color_family_gaps():
    rows = color_gap_rows([
        _ink(id=1, name="Empty Brown", color_family="brown", remaining_ml=0.0, is_empty=True),
        _ink(id=2, name="Royal Blue", color_family="blue", color_type="business blue"),
    ])
    statuses = {(row.family, row.status) for row in rows}
    assert ("brown", "missing") in statuses


def test_v059_grid_and_consumption_helpers_are_preserved_safely():
    samples = [_sample(id=i, ink_id=i) for i in range(1, 6)]
    assert [len(row) for row in build_sample_grid(samples, columns=2)] == [2, 2, 1]
    assert compare_axis_options(samples)["ink"] is True
    assert apply_ink_consumption(2.0, 5.0) == 0.0
    assert apply_ink_consumption(None, 1.0) is None

    status = ink_fill_status(_ink(remaining_ml=2.0, reorder_threshold_ml=5.0))
    assert status["level"] == "reorder"
    assert restock_recommendations([_ink(id=1, remaining_ml=2.0), _ink(id=2, remaining_ml=None)])[0]["id"] == 1
