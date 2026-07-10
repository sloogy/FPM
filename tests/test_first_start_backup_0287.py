import json
import sqlite3

from database.db import dispose_db, get_session, init_db, reinit_db
from database.models import AppSettings, Ink, InkLoad, Pen
from logic.backup_service import create_full_backup, inspect_backup, restore_full_backup
from ui.tour_controller import TourStep, build_steps, execute_step_action, should_show_tour


def _close_db():
    try:
        dispose_db()
    except Exception:
        pass


def test_fresh_database_has_no_example_inks_and_starts_guided_creation(tmp_path):
    _close_db()
    db_path = tmp_path / "fresh.db"
    init_db(db_path)

    session = get_session()
    try:
        assert session.query(Ink).count() == 0
        assert session.query(Pen).count() == 0
        assert AppSettings.get(session, "onboarding_completed") == "0"
    finally:
        session.close()

    assert should_show_tour() is True
    steps = build_steps()
    ids = [step.step_id for step in steps]
    action_pages = [step.page_index for step in steps if step.on_next is not None]
    assert action_pages[:2] == [2, 1]  # Nach der Modulrunde: Tinte, dann Füller
    assert ids.index("expert_intro") < ids.index("nibs") < ids.index("setup_intro")
    assert ids.index("setup_intro") < ids.index("ink_add") < ids.index("pen_add")
    assert ids.index("pen_add") < ids.index("second_pen") < ids.index("rotation_generate")
    assert ids.index("rotation_generate") < ids.index("rotation_apply") < ids.index("rotation_active")
    assert {3, 4, 6, 7, 8, 11, 12, 13} <= {
        step.page_index for step in steps if step.mode == "expert"
    }
    assert next(step for step in steps if step.step_id == "setup_intro").mode == "original"

    with sqlite3.connect(db_path) as connection:
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 0
        # PRAGMA gilt pro Verbindung. Die von SQLAlchemy geöffneten Verbindungen
        # werden separat auf ON gesetzt und unten direkt geprüft.
    session = get_session()
    try:
        assert session.execute(__import__("sqlalchemy").text("PRAGMA foreign_keys")).scalar() == 1
    finally:
        session.close()


def test_full_backup_restores_database_media_cache_and_configuration(tmp_path):
    _close_db()
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    db_path = data_dir / "fpm.db"
    init_db(db_path)

    session = get_session()
    try:
        session.add(Ink(brand="Pilot", name="Tsuki-yo", color_family="blue"))
        session.add(Pen(brand="Pilot", model="Custom 74", fill_system="converter"))
        session.commit()
    finally:
        session.close()

    media = data_dir / "media" / "pens" / "1" / "images" / "pen.jpg"
    media.parent.mkdir(parents=True)
    media.write_bytes(b"image-data")
    (data_dir / "pen_dimensions_cache.json").write_text('{"Pilot Custom 74": {"length_mm": 143}}', encoding="utf-8")
    (data_dir / "manufacturer_domains.json").write_text('{"Pilot": "pilotpen.eu"}', encoding="utf-8")
    (data_dir / "config.json").write_text(json.dumps({"db_path": str(db_path), "custom": "kept"}), encoding="utf-8")

    archive = tmp_path / "collection.fpmbackup"
    result = create_full_backup(archive, data_dir=data_dir, db_path=db_path)
    assert result.path == archive
    manifest = inspect_backup(archive)
    assert "database/fpm.db" in manifest["files"]
    assert "data/media/pens/1/images/pen.jpg" in manifest["files"]
    assert "data/pen_dimensions_cache.json" in manifest["files"]
    assert "data/manufacturer_domains.json" in manifest["files"]

    # Zustand nach dem Backup verändern.
    session = get_session()
    try:
        session.query(Ink).delete()
        session.query(Pen).delete()
        session.commit()
    finally:
        session.close()
    media.write_bytes(b"changed")
    (data_dir / "pen_dimensions_cache.json").unlink()

    dispose_db()
    restored = restore_full_backup(archive, data_dir=data_dir, db_path=db_path)
    assert restored.restored_file_count >= 5
    reinit_db(db_path)

    session = get_session()
    try:
        assert session.query(Ink).filter_by(brand="Pilot", name="Tsuki-yo").count() == 1
        assert session.query(Pen).filter_by(brand="Pilot", model="Custom 74").count() == 1
    finally:
        session.close()
    assert media.read_bytes() == b"image-data"
    assert (data_dir / "pen_dimensions_cache.json").is_file()
    config = json.loads((data_dir / "config.json").read_text(encoding="utf-8"))
    assert config["db_path"] == str(db_path)
    assert config["custom"] == "kept"


def test_existing_database_without_historic_flag_does_not_force_tour(tmp_path):
    _close_db()
    db_path = tmp_path / "existing.db"
    init_db(db_path)
    session = get_session()
    try:
        session.add(Pen(brand="Lamy", model="2000", fill_system="piston"))
        row = session.query(AppSettings).filter_by(key="onboarding_completed").one()
        session.delete(row)
        session.commit()
    finally:
        session.close()

    dispose_db()
    init_db(db_path)
    session = get_session()
    try:
        assert AppSettings.get(session, "onboarding_completed") == "1"
    finally:
        session.close()
    assert should_show_tour() is False


def test_tour_action_abort_and_error_do_not_complete_step():
    window = object()
    assert execute_step_action(TourStep("ok", "ok", on_next=lambda _mw: True), window) is True
    assert execute_step_action(TourStep("cancel", "cancel", on_next=lambda _mw: False), window) is False

    def fail(_mw):
        raise RuntimeError("dialog failed")

    assert execute_step_action(TourStep("fail", "fail", on_next=fail), window) is False


def test_backup_validation_rejects_tampering_and_unlisted_files(tmp_path):
    import zipfile

    _close_db()
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    db_path = data_dir / "fpm.db"
    init_db(db_path)
    archive = create_full_backup(tmp_path / "valid.fpmbackup", data_dir=data_dir, db_path=db_path).path

    tampered = tmp_path / "tampered.fpmbackup"
    with zipfile.ZipFile(archive, "r") as source, zipfile.ZipFile(tampered, "w") as target:
        for info in source.infolist():
            payload = source.read(info.filename)
            if info.filename == "database/fpm.db":
                payload += b"tampered"
            target.writestr(info, payload)
    with __import__("pytest").raises(ValueError, match="Dateigröße|Prüfsumme"):
        inspect_backup(tampered)

    extra = tmp_path / "extra.fpmbackup"
    with zipfile.ZipFile(archive, "r") as source, zipfile.ZipFile(extra, "w") as target:
        for info in source.infolist():
            target.writestr(info, source.read(info.filename))
        target.writestr("data/unlisted.txt", "not in manifest")
    with __import__("pytest").raises(ValueError, match="Manifest"):
        inspect_backup(extra)


def test_schema_upgrade_creates_pre_migration_snapshot_next_to_explicit_database(tmp_path):
    _close_db()
    db_path = tmp_path / "upgrade.db"
    init_db(db_path)
    dispose_db()
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "UPDATE app_settings SET value='0.2.86' WHERE key='schema_version'"
        )
        connection.commit()

    init_db(db_path)
    backups = list((tmp_path / "migration_backups").glob("upgrade_before_0.2.88_*.db"))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as connection:
        assert connection.execute(
            "SELECT value FROM app_settings WHERE key='schema_version'"
        ).fetchone()[0] == "0.2.86"


def test_rotation_workflow_with_one_ink_and_two_empty_pens(tmp_path):
    """Regression: Tour-Daten müssen einen Vorschlag und eine echte Befüllung ergeben."""
    from logic.rotation_engine import RotationEngine

    _close_db()
    db_path = tmp_path / "rotation.db"
    init_db(db_path)
    session = get_session()
    try:
        session.add(Ink(brand="Pilot", name="Tsuki-yo", color_family="blue", color_hex="#24518a"))
        session.add_all(
            [
                Pen(brand="Pilot", model="Custom 74", fill_system="converter"),
                Pen(brand="Lamy", model="2000", fill_system="piston"),
            ]
        )
        session.commit()
    finally:
        session.close()

    engine = RotationEngine()
    suggestions = engine.get_suggestions(5)
    assert suggestions, "Ein leerer aktiver Füller und eine verfügbare Tinte müssen einen Vorschlag ergeben"
    first = suggestions[0]
    ok, message = engine.apply_suggestion(first["pen_id"], first["ink_id"])
    assert ok, message

    session = get_session()
    try:
        assert session.query(InkLoad).filter(InkLoad.cleaned_date.is_(None)).count() == 1
    finally:
        session.close()
    current = engine.get_current_rotation()
    assert len(current) == 1
    assert current[0]["pen_id"] == first["pen_id"]
    assert current[0]["ink_id"] == first["ink_id"]


def test_rotation_toolbar_generates_instead_of_only_refreshing():
    source = (__import__("pathlib").Path(__file__).resolve().parents[1] / "ui" / "main_window.py").read_text(encoding="utf-8")
    assert 'self._run_page_action(5, "generate_suggestions")' in source
    assert 'self._run_page_action(5, "refresh")' not in source
