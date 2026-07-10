"""
Datenbankinitialisierung und Session-Management.

v0.2.4 – Änderbarer Datenbankpfad:
- get_db_path()  liest aus ~/.fpm_data/config.json (Fallback: Default-Pfad)
- set_db_path()  speichert neuen Pfad in config.json
- reinit_db()    schließt die aktuelle Engine und öffnet eine neue DB –
                 kein Neustart nötig.
"""
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from database.models import Base

SCHEMA_VERSION = "0.2.88"

logger = logging.getLogger(__name__)

_STATE = SimpleNamespace(engine=None, session_factory=None)


# ── Config ──────────────────────────────────────────────────────────────────

def _data_dir() -> Path:
    """Return the user data directory.

    Priority:
    1. ``FPM_DATA_DIR`` for portable launchers.
    2. ``installation.json`` next to the frozen app for installer builds.
    3. Compatible default ``~/.fpm_data`` for source/dev installs.
    """
    import os
    import sys

    override = os.environ.get("FPM_DATA_DIR")
    if override:
        d = Path(override).expanduser()
    else:
        marker_dir = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]
        marker = marker_dir / "installation.json"
        d = None
        if marker.exists():
            try:
                data = json.loads(marker.read_text(encoding="utf-8"))
                raw = str(data.get("data_directory", "") or "").strip()
                if raw:
                    d = Path(raw).expanduser()
            except Exception:
                d = None
        if d is None:
            d = Path.home() / ".fpm_data"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _config_path() -> Path:
    return _data_dir() / "config.json"


def _load_config() -> dict:
    p = _config_path()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_config(cfg: dict) -> None:
    _config_path().write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ── Pfad-API ─────────────────────────────────────────────────────────────────

def get_data_dir() -> Path:
    """Gibt den aktiven FPM-Datenordner zurück."""
    return _data_dir()


def get_db_path() -> Path:
    """Gibt den aktuell konfigurierten Datenbankpfad zurück."""
    cfg = _load_config()
    if "db_path" in cfg:
        return Path(cfg["db_path"])
    # Fallback: Standard-Pfad
    return _data_dir() / "fpm.db"


def set_db_path(new_path: Path) -> None:
    """Speichert einen neuen Datenbankpfad in der Config (persistiert über Neustarts)."""
    cfg = _load_config()
    cfg["db_path"] = str(new_path)
    _save_config(cfg)


# ── Initialisierung / Reinitialisierung ──────────────────────────────────────

def init_db(db_path: Path = None) -> None:
    """Initialisiert die Datenbank beim Start."""
    if db_path is None:
        db_path = get_db_path()
    _connect(db_path)


def dispose_db() -> None:
    """Schließt alle DB-Verbindungen, z.B. vor einer Vollwiederherstellung."""
    if _STATE.engine is not None:
        _STATE.engine.dispose()
    _STATE.engine = None
    _STATE.session_factory = None


def reinit_db(new_path: Path) -> None:
    """
    Schließt die aktuelle Engine, speichert den neuen Pfad und öffnet die DB
    unter new_path neu. Alle nachfolgenden get_session()-Aufrufe nutzen
    automatisch die neue Datenbank – kein Neustart nötig.
    """
    dispose_db()
    set_db_path(new_path)
    _connect(new_path)


def _connect(db_path: Path) -> None:
    """Baut Engine + SessionFactory auf und führt Migration/Seed durch.

    Migrationen laufen bewusst fail-fast: Ein teilweise migrierter Datenbestand
    darf nicht unbemerkt weiterverwendet werden. Vor einer echten Migration wird
    die vorhandene SQLite-Datei über die SQLite-Backup-API gesichert.
    """

    # Mehrfachaufrufe aus Tests, Pfadwechseln oder Restore dürfen keine alte
    # Connection-Pool-Instanz offenlassen.
    dispose_db()
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    is_new_database = not db_path.exists() or db_path.stat().st_size == 0
    needs_migration = (not is_new_database) and _database_needs_migration(db_path)
    if needs_migration:
        _backup_before_schema_migration(db_path)

    _STATE.engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        echo=False,
    )

    @event.listens_for(_STATE.engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")
        finally:
            cursor.close()

    Base.metadata.create_all(_STATE.engine)
    _STATE.session_factory = sessionmaker(
        autocommit=False, autoflush=False,
        bind=_STATE.engine, expire_on_commit=False,
    )

    migrations = (
        ("schema", _migrate_schema),
        ("legacy writing samples", _migrate_legacy_writing_samples),
        ("nib formats", _migrate_nib_formats),
        ("legacy nib history", _migrate_legacy_nib_change_events),
        ("pen nib setups", _migrate_pen_nib_setups),
        ("indexes", _ensure_indexes),
    )
    for name, migration in migrations:
        _run_migration(name, migration)

    _insert_default_rules()
    _initialize_onboarding_state(is_new_database)
    _apply_initial_config_settings()
    _validate_database_integrity()



def _run_migration(name: str, migration) -> None:
    try:
        migration()
    except Exception as exc:
        logger.exception("Datenbankmigration '%s' fehlgeschlagen", name)
        raise RuntimeError(f"Datenbankmigration '{name}' fehlgeschlagen: {exc}") from exc


def _database_needs_migration(db_path: Path) -> bool:
    """Prüft ohne SQLAlchemy-Start, ob ein Vor-Migrationsbackup nötig ist."""
    try:
        with sqlite3.connect(db_path) as conn:
            table = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='app_settings'"
            ).fetchone()
            if not table:
                return True
            row = conn.execute(
                "SELECT value FROM app_settings WHERE key='schema_version'"
            ).fetchone()
            return row is None or str(row[0] or "") != SCHEMA_VERSION
    except sqlite3.Error:
        return True


def _initialize_onboarding_state(is_new_database: bool) -> None:
    """Initialisiert den Erststart ohne Beispiel-Datensätze.

    Neue Datenbanken starten die geführte Anlage. Bestehende Datenbanken ohne
    historisches Flag werden nicht überraschend erneut durch die Tour geführt.
    Ein manueller Reset setzt das Flag später wieder auf ``0``.
    """
    from database.models import AppSettings

    session = _STATE.session_factory()
    try:
        if AppSettings.get(session, "onboarding_completed") is None:
            AppSettings.set(session, "onboarding_completed", "0" if is_new_database else "1")
    finally:
        session.close()


def _ensure_indexes() -> None:
    """Legt häufig benötigte Filter-/Verknüpfungsindizes idempotent an."""
    statements = (
        "CREATE INDEX IF NOT EXISTS ix_pens_brand_model ON pens(brand, model)",
        "CREATE INDEX IF NOT EXISTS ix_inks_brand_name ON inks(brand, name)",
        "CREATE INDEX IF NOT EXISTS ix_ink_loads_pen_active ON ink_loads(pen_id, cleaned_date)",
        "CREATE INDEX IF NOT EXISTS ix_ink_loads_ink_date ON ink_loads(ink_id, loaded_date)",
        "CREATE INDEX IF NOT EXISTS ix_expenses_date_type ON expenses(purchase_date, item_type)",
        "CREATE INDEX IF NOT EXISTS ix_wishlist_status ON wishlist_items(status)",
        "CREATE INDEX IF NOT EXISTS ix_writing_samples_date_pen ON writing_samples(written_at, pen_id)",
        "CREATE INDEX IF NOT EXISTS ix_cleaning_logs_date_pen ON cleaning_logs(cleaned_at, pen_id)",
    )
    with _STATE.engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))


def _validate_database_integrity() -> None:
    """Bricht bei beschädigter DB oder verwaisten Fremdschlüsseln klar ab."""
    with _STATE.engine.connect() as conn:
        integrity = conn.execute(text("PRAGMA integrity_check")).scalar()
        if str(integrity).lower() != "ok":
            raise RuntimeError(f"SQLite-Integritätsprüfung fehlgeschlagen: {integrity}")
        violations = conn.execute(text("PRAGMA foreign_key_check")).fetchall()
        if violations:
            sample = ", ".join(str(tuple(row)) for row in violations[:5])
            raise RuntimeError(
                f"Die Datenbank enthält {len(violations)} ungültige Fremdschlüssel. "
                f"Beispiele: {sample}"
            )


def _apply_initial_config_settings() -> None:
    """Installer-/Portable-Erstwerte aus config.json in AppSettings uebernehmen.

    Der Installer legt config.json im gewaehlten Datenordner an, bevor die App
    zum ersten Mal startet. Bestehende Nutzereinstellungen werden nie
    ueberschrieben.
    """
    try:
        cfg = _load_config()
    except Exception:
        return
    initial = cfg.get("initial_settings") if isinstance(cfg, dict) else None
    if not isinstance(initial, dict) or _STATE.session_factory is None:
        return
    allowed = {
        "language",
        "default_currency",
        "locale_region",
        "locale_decimal_sep",
        "locale_thousands_sep",
        "locale_currency_position",
    }
    from database.models import AppSettings

    session = _STATE.session_factory()
    try:
        for key, value in initial.items():
            if key not in allowed:
                continue
            if AppSettings.get(session, key) is None:
                session.add(AppSettings(key=key, value=str(value)))
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()

def get_session() -> Session:
    if _STATE.session_factory is None:
        raise RuntimeError("Datenbank nicht initialisiert – init_db() zuerst aufrufen.")
    return _STATE.session_factory()


# ── Seed-Daten ───────────────────────────────────────────────────────────────

def _insert_default_rules():
    """Eingebaute Systemregeln einfügen (nur einmalig pro DB)."""
    import json as _json
    from database.models import Rule, AppSettings

    session = _STATE.session_factory()
    try:
        rules = [
            Rule(
                name="Shimmer-Tinte in Vac-Füller vermeiden",
                description="Shimmer-Partikel können den Vac-Mechanismus beschädigen.",
                rule_type="hard", warn_level="blocked",
                condition_type="fill_system_ink_prop",
                rule_group="ink_fill", auto_action="reject", score_delta=-90,
                condition_data=_json.dumps({"fill_system": "vac", "prop": "has_shimmer", "value": True}),
                is_system=True,
            ),
            Rule(
                name="Pigmenttinte in Vac-Füller vermeiden",
                description="Pigmentierte Tinten können den Vac-Mechanismus verstopfen.",
                rule_type="hard", warn_level="blocked",
                condition_type="fill_system_ink_prop",
                rule_group="ink_fill", auto_action="reject", score_delta=-90,
                condition_data=_json.dumps({"fill_system": "vac", "prop": "is_pigment", "value": True}),
                is_system=True,
            ),
            Rule(
                name="Shimmer-Tinte in Eyedropper",
                description="Shimmer-Tinten können in Eyedropper-Füllern sedimentieren.",
                rule_type="soft", warn_level="warning",
                condition_type="fill_system_ink_prop",
                rule_group="ink_fill", auto_action="warn", score_delta=-30,
                condition_data=_json.dumps({"fill_system": "eyedropper", "prop": "has_shimmer", "value": True}),
                is_system=True,
            ),
            Rule(
                name="EF-Feder: nasse Tinte bevorzugen",
                description="Extra-feine Federn schreiben besser mit nassen Tinten (Nassskala ≥ 3).",
                rule_type="soft", warn_level="info",
                condition_type="nib_size_wetness",
                rule_group="nib", auto_action="warn", score_delta=-18,
                condition_data=_json.dumps({"nib_size": "EF", "wetness_min": 3}),
                is_system=True,
            ),
            Rule(
                name="Wasserfeste Tinte: Reinigungshinweis",
                description="Wasserfeste Tinten erfordern intensive Reinigung.",
                rule_type="soft", warn_level="info",
                condition_type="ink_prop_warning",
                rule_group="maintenance", auto_action="warn", score_delta=-12,
                condition_data=_json.dumps({"prop": "is_waterproof", "value": True}),
                is_system=True,
            ),
            Rule(
                name="Grail-Füller: keine Shimmer-Tinte",
                description="Grail Pens sollen standardmäßig keine Shimmer-Tinte bekommen.",
                rule_type="soft", warn_level="critical",
                condition_type="pen_tag_ink_prop",
                rule_group="collector", auto_action="require_override", score_delta=-60,
                condition_data=_json.dumps({"tag": "grail", "prop": "has_shimmer", "value": True}),
                is_system=True,
            ),
            Rule(
                name="Grail-Füller: keine schwer reinigbare Sheen-Tinte",
                description="Grail Pens bevorzugen sichere, gut reinigbare Tinten.",
                rule_type="soft", warn_level="warning",
                condition_type="pen_tag_sheen_cleaning",
                rule_group="collector", auto_action="warn", score_delta=-25,
                condition_data=_json.dumps({"tag": "grail", "cleaning_min": 4}),
                is_system=True,
            ),
            Rule(
                name="Stub/Flex: Sheen bevorzugen",
                description="Breite oder flexible Federn zeigen Sheen/Shading besonders gut.",
                rule_type="preference", warn_level="info",
                condition_type="nib_grind_prefers_ink_prop",
                rule_group="nib", auto_action="allow", score_delta=-8,
                condition_data=_json.dumps({"grinds": ["stub", "italic", "flex"], "props": ["has_sheen", "has_shading"]}),
                is_system=True,
            ),
        ]
        # Systemregeln werden nur angelegt, wenn sie fehlen. Bestehende Systemregeln
        # dürfen Nutzer anpassen; diese Anpassungen werden beim Neustart nicht mehr
        # vom Katalog überschrieben.
        existing_by_name = {r.name: r for r in session.query(Rule).filter_by(is_system=True).all()}
        for r in rules:
            existing = existing_by_name.get(r.name)
            if existing:
                # Systemregeln sind editierbar. Ein vorhandener Eintrag darf beim
                # App-Start nicht mehr auf Katalogwerte zurückgesetzt werden.
                # Nur das System-Flag bleibt gesichert; Aktiv/Inaktiv und alle
                # fachlichen Felder bleiben Nutzerentscheidung.
                existing.is_system = True
            else:
                session.add(r)

        from database.models import AppSettings
        import json as _json2
        defaults = {
            "cleaning_days_normal":  "28",
            "cleaning_days_shimmer": "14",
            "cleaning_days_pigment": "10",
            "cleaning_days_grail":   "21",
            # Region & Währung (Schweiz als Standard)
            "default_currency":            "CHF",
            "locale_decimal_sep":          ".",
            "locale_thousands_sep":        "'",
            "locale_currency_position":    "before",
            "locale_region":               "CH",
            "exchange_rates_json": _json2.dumps({
                "CHF": 1.0,
                "EUR": 0.95,
                "USD": 1.08,
                "GBP": 0.81,
            }),
            # Expertensystem / Auto Mode
            "rules_enabled": "1",
            "full_auto_mode": "0",
            "full_auto_can_reject": "1",
            "full_auto_can_override": "0",
            "full_auto_logging": "1",
            "rotation_allow_active_ink_duplicates": "0",
            # v0.2.80: Zufälligkeit der Vorschläge in Prozent (Schutzregeln bleiben aktiv)
            "rotation_randomness_percent": "0",
            "ui_mode": "easy",
            "ui_scale_mode": "auto",
            "rule_group_safety_enabled": "1",
            "rule_group_maintenance_enabled": "1",
            "rule_group_rotation_enabled": "1",
            "rule_group_pen_enabled": "1",
            "rule_group_ink_enabled": "1",
            "rule_group_ink_fill_enabled": "1",
            "rule_group_consumption_enabled": "0",
            "rule_group_nib_enabled": "1",
            "rule_group_paper_enabled": "1",
            "rule_group_collector_enabled": "1",
        }
        for k, v in defaults.items():
            if AppSettings.get(session, k) is None:
                AppSettings.set(session, k, v)

        session.commit()
    finally:
        session.close()


def insert_example_inks():
    """Legt optionale Demonstrations-Tinten an. Wird niemals automatisch aufgerufen."""
    from datetime import datetime
    from database.models import Ink
    session = _STATE.session_factory()
    try:
        rows = [
            dict(brand="Diamine", name="Skull & Roses", color_type="Sheen-Monster", color_family="blue", color_hex="#1D2C73", wetness_level=4, has_sheen=True, sheen_level=5, sheen_color="rot", has_shimmer=False, feathering_level=4, shading_level=3, flow_level=4, saturation_level=5, cleaning_effort=4, max_days_in_pen=14, notes="Extrem sheen-lastig, ideal auf Tomoe River"),
            dict(brand="Diamine", name="Writer’s Blood", color_type="Dunkles Rotbraun", color_family="red", color_hex="#5A1F2B", wetness_level=5, has_sheen=True, sheen_level=2, sheen_color="gold", has_shimmer=False, feathering_level=3, shading_level=1, flow_level=5, saturation_level=5, cleaning_effort=3, notes="Perfekt für trockene EF-Federn"),
            dict(brand="Diamine", name="Communication Breakdown", color_type="Dusty Magenta/Violett", color_family="purple", color_hex="#7A4A63", wetness_level=3, has_sheen=True, sheen_level=1, has_shimmer=False, feathering_level=2, shading_level=4, flow_level=4, saturation_level=3, cleaning_effort=1, notes="Künstlerische Vintage-Farbe"),
            dict(brand="Diamine", name="Earl Grey", color_type="Kühles Grau", color_family="grey", color_hex="#6C7075", wetness_level=2, has_sheen=False, sheen_level=0, has_shimmer=False, feathering_level=1, shading_level=4, flow_level=3, saturation_level=3, cleaning_effort=1, notes="Hervorragend für EF und Alltag"),
            dict(brand="Diamine", name="Aurora Borealis", color_type="Petrol/Türkisgrün", color_family="teal", color_hex="#006D6F", wetness_level=4, has_sheen=True, sheen_level=1, sheen_color="rot", has_shimmer=False, feathering_level=1, shading_level=3, flow_level=5, saturation_level=4, cleaning_effort=1, notes="Einer der besten Allrounder"),
            dict(brand="Pelikan Edelstein", name="Aventurine", color_type="Dunkelgrün", color_family="green", color_hex="#006B45", wetness_level=3, has_sheen=True, sheen_level=1, has_shimmer=False, feathering_level=1, shading_level=3, flow_level=4, saturation_level=4, cleaning_effort=1, notes="Elegantes Waldgrün"),
            dict(brand="Pelikan Edelstein", name="Topaz", color_type="Türkisblau", color_family="turquoise", color_hex="#0099A8", wetness_level=3, has_sheen=False, sheen_level=0, has_shimmer=False, feathering_level=1, shading_level=4, flow_level=4, saturation_level=3, cleaning_effort=1, notes="Sehr sauberer Business-Türkis"),
            dict(brand="Pelikan Edelstein", name="Sapphire", color_type="Royalblau", color_family="blue", color_hex="#1D3F91", wetness_level=3, has_sheen=True, sheen_level=1, sheen_color="rot", has_shimmer=False, feathering_level=1, shading_level=3, flow_level=4, saturation_level=4, cleaning_effort=1, notes="Seriös mit Tiefe"),
            dict(brand="Pelikan Edelstein", name="Jade", color_type="Smaragdgrün", color_family="green", color_hex="#008B6B", wetness_level=3, has_sheen=False, sheen_level=0, has_shimmer=False, feathering_level=1, shading_level=3, flow_level=4, saturation_level=3, cleaning_effort=1, notes="Kühler als Aventurine"),
            dict(brand="Caran d’Ache Chromatics", name="Magnetic Blue", color_type="Tiefblau", color_family="blue", color_hex="#003D8F", wetness_level=4, has_sheen=True, sheen_level=1, sheen_color="Gold/Rot", has_shimmer=False, feathering_level=2, shading_level=3, flow_level=5, saturation_level=4, cleaning_effort=3, notes="Sehr luxuriöser Fluss"),
            dict(brand="Pilot Iroshizuku", name="Asa-gao", color_type="Klarblau", color_family="blue", color_hex="#2E52D1", wetness_level=5, has_sheen=True, sheen_level=1, sheen_color="rot", has_shimmer=False, feathering_level=1, shading_level=3, flow_level=5, saturation_level=4, cleaning_effort=1, notes="Extrem gute Schmierung, ideal für EF"),
            dict(brand="Graf von Faber-Castell", name="Deep Sea Green", color_type="Petrolgrün", color_family="teal", color_hex="#234C4A", wetness_level=2, has_sheen=False, sheen_level=0, has_shimmer=False, feathering_level=1, shading_level=4, flow_level=3, saturation_level=3, cleaning_effort=1, notes="Edel, weich schattierend, extrem bürotauglich"),
        ]
        for data in rows:
            exists = session.query(Ink).filter_by(brand=data["brand"], name=data["name"]).first()
            if not exists:
                session.add(Ink(purchase_date=datetime.now(), **data))
        session.commit()
    finally:
        session.close()


# ── Schema-Migration ──────────────────────────────────────────────────────────

def _backup_before_schema_migration(db_path: Path) -> None:
    """Sichert den unveränderten Vor-Migrationszustand über SQLite ``backup``."""
    db_path = Path(db_path)
    if not db_path.exists():
        return
    configured_db = get_db_path().expanduser().resolve()
    backup_root = _data_dir() if configured_db == db_path.expanduser().resolve() else db_path.parent
    backup_dir = backup_root / "migration_backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = backup_dir / f"{db_path.stem}_before_{SCHEMA_VERSION}_{stamp}{db_path.suffix}"
    try:
        with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as source:
            with sqlite3.connect(target) as destination:
                source.backup(destination)
    except sqlite3.Error as exc:
        logger.exception("Vor-Migrationsbackup fehlgeschlagen: %s", target)
        raise RuntimeError(f"Vor-Migrationsbackup konnte nicht erstellt werden: {exc}") from exc

def _migrate_schema():
    """Fügt neue Spalten hinzu ohne bestehende DB zu löschen."""
    from sqlalchemy import text
    migrations = [
        ("pens",      "length_uncapped_mm",       "FLOAT"),
        ("pens",      "length_posted_mm",         "FLOAT"),
        ("pens",      "section_diameter_mm",      "FLOAT"),
        ("pens",      "compatible_nibs",          "TEXT"),
        ("pens",      "incompatible_nibs",         "TEXT"),
        ("nibs",      "physical_size",             "VARCHAR(30)"),
        ("nibs",      "is_proprietary",            "BOOLEAN DEFAULT 0"),
        ("pens",      "ink_capacity_ml",           "FLOAT"),
        ("pens",      "popularity_rating",         "INTEGER DEFAULT 3"),
        ("pens",      "must_include_in_rotation",  "BOOLEAN DEFAULT 0"),
        ("pens",      "fixed_ink_id",              "INTEGER"),
        ("pens",      "rotation_role",             "VARCHAR(50) DEFAULT 'writer'"),
        ("pens",      "rotation_theme",            "VARCHAR(50)"),
        ("ink_loads", "volume_ml",                 "FLOAT"),
        ("ink_loads", "is_fixed_pairing",          "BOOLEAN DEFAULT 0"),
        ("pens",      "availability_status",      "VARCHAR(30) DEFAULT 'available'"),
        ("pens",      "rotation_blocked",         "BOOLEAN DEFAULT 0"),
        ("pens",      "blocked_until",            "DATETIME"),
        ("pens",      "service_start_date",       "DATETIME"),
        ("pens",      "service_days",             "INTEGER"),
        ("pens",      "service_cost",             "FLOAT"),
        ("pens",      "service_currency",         "VARCHAR(3)"),
        ("pens",      "service_notes",            "TEXT"),
        ("pens",      "purchase_currency",        "VARCHAR(3)"),
        ("pens",      "market_currency",          "VARCHAR(3)"),
        ("pens",      "insurance_currency",       "VARCHAR(3)"),
        ("nibs",      "material",                 "VARCHAR(50)"),
        # 0.2.35: Trennung Format/Exemplar + zusätzliche Feel-Felder
        ("nibs",      "format_id",                "INTEGER REFERENCES nib_formats(id)"),
        ("nibs",      "source",                   "VARCHAR(100)"),
        ("nibs",      "feed_type",                "VARCHAR(50)"),
        ("nibs",      "feed_notes",               "TEXT"),
        ("nibs",      "stiffness_level",          "INTEGER DEFAULT 4"),
        ("nibs",      "tuning_notes",             "TEXT"),
        ("nibs",      "label",                    "VARCHAR(120)"),
        ("nibs",      "feedback_level",           "INTEGER DEFAULT 3"),
        ("nib_formats", "compatible_with",       "TEXT"),
        ("nib_formats", "notes",                 "TEXT"),
        ("pen_nib_setups", "is_active",          "BOOLEAN DEFAULT 1"),
        ("pen_nib_setups", "installed_date",     "DATETIME"),
        ("pen_nib_setups", "removed_date",       "DATETIME"),
        ("pen_nib_setups", "setup_label",        "VARCHAR(150)"),
        ("pen_nib_setups", "install_reason",     "TEXT"),
        ("pen_nib_setups", "removal_reason",     "TEXT"),
        ("pen_nib_setups", "feed_type",          "VARCHAR(80)"),
        ("pen_nib_setups", "feed_notes",         "TEXT"),
        ("pen_nib_setups", "flow_level",         "INTEGER DEFAULT 3"),
        ("pen_nib_setups", "wetness_feel_level", "INTEGER DEFAULT 3"),
        ("pen_nib_setups", "stiffness_feel_level", "INTEGER DEFAULT 3"),
        ("pen_nib_setups", "feedback_level",     "INTEGER DEFAULT 3"),
        ("pen_nib_setups", "compatibility_notes", "TEXT"),
        ("pen_nib_setups", "feel_notes",         "TEXT"),
        ("pen_nib_setups", "created_at",         "DATETIME"),
        ("pen_nib_setups", "updated_at",         "DATETIME"),
        ("inks",      "purchase_currency",       "VARCHAR(3)"),
        ("inks",      "reorder_threshold_ml",     "FLOAT"),
        ("inks",      "reorder_url",              "VARCHAR(1000)"),
        ("inks",      "reorder_note",             "TEXT"),
        ("inks",      "is_empty",                 "BOOLEAN DEFAULT 0"),
        ("inks",      "is_archived",              "BOOLEAN DEFAULT 0"),
        ("inks",      "color_type",               "VARCHAR(100)"),
        ("inks",      "sheen_level",              "INTEGER DEFAULT 0"),
        ("inks",      "sheen_color",              "VARCHAR(50)"),
        ("inks",      "feathering_level",         "INTEGER DEFAULT 2"),
        ("inks",      "shading_level",            "INTEGER DEFAULT 3"),
        ("inks",      "flow_level",               "INTEGER DEFAULT 3"),
        ("inks",      "saturation_level",         "INTEGER DEFAULT 3"),
        ("inks",      "character_notes",          "TEXT"),
        ("inks",      "usage_tags",               "TEXT"),
        ("papers",    "purchase_currency",       "VARCHAR(3)"),
        ("papers",    "image_path",              "VARCHAR(500)"),
        ("expenses",  "nib_id",                   "INTEGER"),
        ("expenses",  "paper_id",                 "INTEGER"),
        ("expenses",  "vendor",                   "VARCHAR(150)"),
        ("expenses",  "order_number",             "VARCHAR(100)"),
        ("expenses",  "payment_method",           "VARCHAR(80)"),
        ("expenses",  "warranty_until",           "DATETIME"),
        ("rules",     "rule_group",              "VARCHAR(50) DEFAULT 'rotation'"),
        ("rules",     "score_delta",             "INTEGER"),
        ("rules",     "auto_action",             "VARCHAR(30) DEFAULT 'warn'"),
        ("override_logs", "decision_mode",       "VARCHAR(30) DEFAULT 'manual'"),
        ("override_logs", "action",              "VARCHAR(50)"),
        ("override_logs", "score_snapshot",      "INTEGER"),
        ("override_logs", "explanation",         "TEXT"),
        ("writing_samples", "title",            "VARCHAR(200)"),
        ("writing_samples", "sample_type",      "VARCHAR(40) DEFAULT 'regular'"),
        ("writing_samples", "nib_id",           "INTEGER"),
        ("writing_samples", "written_at",       "DATETIME"),
        ("writing_samples", "sample_text",      "TEXT"),
        ("writing_samples", "line_width_mm",    "FLOAT"),
        ("writing_samples", "dry_time_seconds", "FLOAT"),
        ("writing_samples", "feathering_level", "INTEGER DEFAULT 1"),
        ("writing_samples", "bleedthrough_level", "INTEGER DEFAULT 1"),
        ("writing_samples", "shading_level",    "INTEGER DEFAULT 3"),
        ("writing_samples", "sheen_level",      "INTEGER DEFAULT 0"),
        ("writing_samples", "flow_level",       "INTEGER DEFAULT 3"),
        ("writing_samples", "feedback_level",   "INTEGER DEFAULT 3"),
        ("writing_samples", "overall_rating",   "INTEGER DEFAULT 3"),
        ("writing_samples", "tags",             "TEXT"),
        ("writing_samples", "updated_at",       "DATETIME"),
        ("cleaning_logs", "pen_id",             "INTEGER"),
        ("cleaning_logs", "ink_id",             "INTEGER"),
        ("cleaning_logs", "cleaned_at",         "DATETIME"),
        ("cleaning_logs", "duration_minutes",   "FLOAT"),
        ("cleaning_logs", "difficulty_level",   "INTEGER DEFAULT 3"),
        ("cleaning_logs", "flush_cycles",       "INTEGER"),
        ("cleaning_logs", "cleaner_used",       "VARCHAR(120)"),
        ("cleaning_logs", "result",             "VARCHAR(50)"),
        ("cleaning_logs", "notes",              "TEXT"),
        ("cleaning_logs", "created_at",         "DATETIME"),
        ("cleaning_logs", "updated_at",         "DATETIME"),
        ("wishlist_items", "item_type",          "VARCHAR(30) DEFAULT 'pen'"),
        ("wishlist_items", "title",              "VARCHAR(200)"),
        ("wishlist_items", "brand",              "VARCHAR(100)"),
        ("wishlist_items", "model",              "VARCHAR(150)"),
        ("wishlist_items", "variant",            "VARCHAR(150)"),
        ("wishlist_items", "status",             "VARCHAR(30) DEFAULT 'wish'"),
        ("wishlist_items", "priority",           "INTEGER DEFAULT 3"),
        ("wishlist_items", "desired_price",      "FLOAT"),
        ("wishlist_items", "expected_price",     "FLOAT"),
        ("wishlist_items", "actual_price",       "FLOAT"),
        ("wishlist_items", "currency",           "VARCHAR(3)"),
        ("wishlist_items", "shipping",           "FLOAT"),
        ("wishlist_items", "customs",            "FLOAT"),
        ("wishlist_items", "shop",               "VARCHAR(150)"),
        ("wishlist_items", "url",                "VARCHAR(1000)"),
        ("wishlist_items", "reason",             "TEXT"),
        ("wishlist_items", "notes",              "TEXT"),
        ("wishlist_items", "article_card_path",  "VARCHAR(1000)"),
        ("wishlist_items", "bought_date",        "DATETIME"),
        ("wishlist_items", "created_object_type", "VARCHAR(30)"),
        ("wishlist_items", "created_object_id",  "INTEGER"),
        ("wishlist_items", "created_at",         "DATETIME"),
        ("wishlist_items", "updated_at",         "DATETIME"),
    ]
    with _STATE.engine.begin() as conn:
        for table, column, coltype in migrations:
            existing = [row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))]
            if column not in existing:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}"))
        # schema_version ist bewusst als AppSetting gespeichert, damit spätere
        # Migrationen nachvollziehbar bleiben. Tabelle existiert durch create_all().
        existing_settings = [row[1] for row in conn.execute(text("PRAGMA table_info(app_settings)"))]
        if "key" in existing_settings and "value" in existing_settings:
            has_version = conn.execute(text("SELECT value FROM app_settings WHERE key='schema_version'")).fetchone()
            if has_version is None:
                conn.execute(text("INSERT INTO app_settings(key, value) VALUES ('schema_version', :schema_version)"), {"schema_version": SCHEMA_VERSION})
            else:
                conn.execute(text("UPDATE app_settings SET value=:schema_version WHERE key='schema_version'"), {"schema_version": SCHEMA_VERSION})





def _table_columns(conn, table: str) -> set[str]:
    """Gibt vorhandene SQLite-Spalten zurück; fehlende Tabellen ergeben set()."""
    try:
        return {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
    except Exception:
        return set()


def _table_exists(conn, table: str) -> bool:
    row = conn.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name=:name"),
        {"name": table},
    ).fetchone()
    return row is not None


def _migrate_legacy_writing_samples() -> None:
    """Übernimmt v0.2.59-Schreibproben sicher in das neue Modell.

    Die alternative v0.2.59-Linie hatte bereits eine Tabelle ``writing_samples``,
    aber nur mit Bildpfad, Notizen und ``nib_desc``. ``create_all()`` verändert
    bestehende Tabellen nicht; ohne diese Migration würden spätere ORM-Zugriffe
    auf ``title``, ``written_at`` oder Bewertungsfelder bei bestehenden Nutzern
    scheitern. Die Migration ist idempotent und bewahrt ``nib_desc`` in den
    Notizen, falls noch kein strukturiertes ``nib_id`` existiert.
    """
    if _STATE.engine is None:
        return
    now = datetime.now().isoformat(sep=" ", timespec="seconds")
    with _STATE.engine.begin() as conn:
        if not _table_exists(conn, "writing_samples"):
            return
        cols = _table_columns(conn, "writing_samples")
        if "title" not in cols:
            return

        updates = [
            ("sample_type", "'regular'"),
            ("written_at", "COALESCE(created_at, :now)" if "created_at" in cols else ":now"),
            ("feathering_level", "1"),
            ("bleedthrough_level", "1"),
            ("shading_level", "3"),
            ("sheen_level", "0"),
            ("flow_level", "3"),
            ("feedback_level", "3"),
            ("overall_rating", "3"),
            ("updated_at", "COALESCE(created_at, :now)" if "created_at" in cols else ":now"),
        ]
        for column, default_sql in updates:
            if column in cols:
                conn.execute(
                    text(f"UPDATE writing_samples SET {column} = {default_sql} WHERE {column} IS NULL"),
                    {"now": now},
                )

        rows = conn.execute(text("""
            SELECT ws.id,
                   COALESCE(ws.title, '') AS title,
                   COALESCE(ws.notes, '') AS notes,
                   p.brand AS pen_brand, p.model AS pen_model,
                   i.brand AS ink_brand, i.name AS ink_name,
                   pa.brand AS paper_brand, pa.name AS paper_name
            FROM writing_samples ws
            LEFT JOIN pens p ON p.id = ws.pen_id
            LEFT JOIN inks i ON i.id = ws.ink_id
            LEFT JOIN papers pa ON pa.id = ws.paper_id
        """)).mappings().all()
        has_nib_desc = "nib_desc" in cols
        for row in rows:
            parts: list[str] = []
            pen = " ".join(v for v in (row["pen_brand"], row["pen_model"]) if v)
            ink = " ".join(v for v in (row["ink_brand"], row["ink_name"]) if v)
            paper = " ".join(v for v in (row["paper_brand"], row["paper_name"]) if v)
            for part in (pen, ink, paper):
                if part:
                    parts.append(part)
            title = (row["title"] or "").strip() or (" · ".join(parts) if parts else f"Schreibprobe #{row['id']}")
            conn.execute(
                text("UPDATE writing_samples SET title=:title WHERE id=:id AND (title IS NULL OR TRIM(title)='')"),
                {"title": title, "id": row["id"]},
            )
            if has_nib_desc:
                nib_desc = conn.execute(
                    text("SELECT nib_desc FROM writing_samples WHERE id=:id"),
                    {"id": row["id"]},
                ).scalar()
                nib_desc = (nib_desc or "").strip()
                notes = (row["notes"] or "").strip()
                if nib_desc and "Legacy-Feder:" not in notes:
                    merged = (notes + "\n\n" if notes else "") + f"Legacy-Feder: {nib_desc}"
                    conn.execute(text("UPDATE writing_samples SET notes=:notes WHERE id=:id"), {"notes": merged, "id": row["id"]})


def _migrate_legacy_nib_change_events() -> None:
    """Überführt alte v0.2.59-``nib_change_events`` in ``pen_nib_setups``.

    Die Zielarchitektur hat bewusst nur eine Feder-Wahrheit: ``pen_nib_setups``.
    Alte Eventdaten werden daher als Setup-Historie importiert. Events ohne
    ``nib_id`` bleiben unangetastet, weil die Setup-Tabelle eine echte Feder
    benötigt. Die Migration ist idempotent und erzeugt keine Dubletten.
    """
    if _STATE.engine is None:
        return
    now = datetime.now().isoformat(sep=" ", timespec="seconds")
    with _STATE.engine.begin() as conn:
        if not _table_exists(conn, "nib_change_events") or not _table_exists(conn, "pen_nib_setups"):
            return
        events = conn.execute(text("""
            SELECT id, pen_id, nib_id, nib_label, changed_date, reason
            FROM nib_change_events
            WHERE pen_id IS NOT NULL AND nib_id IS NOT NULL
            ORDER BY pen_id, changed_date, id
        """)).mappings().all()
        by_pen: dict[int, list[dict]] = {}
        for event in events:
            by_pen.setdefault(int(event["pen_id"]), []).append(dict(event))
        for pen_id, rows in by_pen.items():
            for idx, event in enumerate(rows):
                installed = event.get("changed_date") or now
                removed = rows[idx + 1].get("changed_date") if idx + 1 < len(rows) else None
                exists = conn.execute(text("""
                    SELECT id FROM pen_nib_setups
                    WHERE pen_id=:pen_id AND nib_id=:nib_id AND COALESCE(installed_date, '') = COALESCE(:installed, '')
                """), {"pen_id": pen_id, "nib_id": event["nib_id"], "installed": installed}).fetchone()
                if exists:
                    continue
                conn.execute(text("""
                    INSERT INTO pen_nib_setups(
                        pen_id, nib_id, is_active, installed_date, removed_date,
                        setup_label, install_reason, removal_reason,
                        flow_level, wetness_feel_level, stiffness_feel_level, feedback_level,
                        feel_notes, created_at, updated_at
                    ) VALUES (
                        :pen_id, :nib_id, :is_active, :installed, :removed,
                        :label, :reason, :removal_reason,
                        3, 3, 3, 3,
                        :feel_notes, :now, :now
                    )
                """), {
                    "pen_id": pen_id,
                    "nib_id": event["nib_id"],
                    "is_active": 1 if removed is None else 0,
                    "installed": installed,
                    "removed": removed,
                    "label": event.get("nib_label") or None,
                    "reason": event.get("reason") or "Aus alter Federhistorie migriert.",
                    "removal_reason": "Durch späteren Federwechsel ersetzt." if removed else None,
                    "feel_notes": "Aus v0.2.59 nib_change_events in pen_nib_setups übernommen.",
                    "now": now,
                })

def _migrate_nib_formats() -> None:
    """Stellt sicher, dass jede bestehende Nib einem NibFormat zugeordnet ist.

    - Findet/erzeugt pro (manufacturer, physical_size, is_proprietary)-Tupel
      ein NibFormat und setzt nib.format_id.
    - Übernimmt is_flexible=True in stiffness_level=2 (weich), wenn noch
      auf Default (4) gesetzt.
    - Idempotent: läuft bei jedem Start, ändert aber nichts, wenn alles passt.
    """
    from database.models import Nib, NibFormat
    if _STATE.session_factory is None:
        return
    session = _STATE.session_factory()
    try:
        nibs = session.query(Nib).all()
        if not nibs:
            return
        # Format-Cache: (mfr_lower, phys_lower, prop) -> NibFormat
        cache: dict[tuple, NibFormat] = {}
        for fmt in session.query(NibFormat).all():
            key = ((fmt.manufacturer or "").strip().lower(),
                   (fmt.physical_size or "").strip().lower(),
                   bool(fmt.is_proprietary))
            cache[key] = fmt
        changed = False
        for nib in nibs:
            # Format zuweisen, falls noch keins
            if nib.format_id is None:
                mfr = (nib.manufacturer or "").strip()
                phys = (nib.physical_size or "").strip()
                prop = bool(nib.is_proprietary)
                if mfr or phys:
                    key = (mfr.lower(), phys.lower(), prop)
                    fmt = cache.get(key)
                    if fmt is None:
                        fmt = NibFormat(
                            manufacturer=mfr or "Unbekannt",
                            physical_size=phys or None,
                            is_proprietary=prop,
                        )
                        session.add(fmt); session.flush()
                        cache[key] = fmt
                    nib.format_id = fmt.id
                    changed = True
            # Steifigkeit aus is_flexible ableiten (nur wenn noch Default 4)
            if getattr(nib, "is_flexible", False) and (nib.stiffness_level or 4) == 4:
                nib.stiffness_level = 2
                changed = True
        if changed:
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _migrate_pen_nib_setups() -> None:
    """Erzeugt aktive PenNibSetup-Einträge aus bestehenden pen.nib_id-Zuweisungen.

    Idempotent: Wenn ein Füller bereits ein aktives Setup hat, wird nichts neu
    erzeugt. Das alte Pen.nib_id bleibt als Backward-Compatible Cache erhalten.
    """
    from database.models import Pen, PenNibSetup
    if _STATE.session_factory is None:
        return
    session = _STATE.session_factory()
    try:
        changed = False
        for pen in session.query(Pen).all():
            if not getattr(pen, "nib_id", None):
                continue
            active = None
            for setup in list(getattr(pen, "nib_setups", []) or []):
                if setup.is_active and setup.removed_date is None:
                    active = setup
                    break
            if active is not None:
                continue
            nib = pen.nib
            setup = PenNibSetup(
                pen_id=pen.id,
                nib_id=pen.nib_id,
                feed_type=getattr(nib, "feed_type", None) if nib else None,
                feed_notes=getattr(nib, "feed_notes", None) if nib else None,
                flow_level=3,
                wetness_feel_level=3,
                stiffness_feel_level=int(getattr(nib, "stiffness_level", 3) or 3) if nib else 3,
                feedback_level=int(getattr(nib, "feedback_level", 3) or 3) if nib else 3,
                feel_notes="Automatisch aus vorhandener Füller-Feder-Zuweisung migriert.",
            )
            session.add(setup)
            changed = True
        if changed:
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ── Reset-Funktionen ─────────────────────────────────────────────────────────

def reset_inkloads(keep_history: bool = True) -> int:
    """
    Aktive InkLoads schließen (cleaned_date = jetzt).
    keep_history=False → gesamte InkLoad-Tabelle leeren.
    Gibt Anzahl betroffener Einträge zurück.
    """
    from datetime import datetime
    from database.models import InkLoad
    session = _STATE.session_factory()
    try:
        now = datetime.now()
        if keep_history:
            active = session.query(InkLoad).filter(InkLoad.cleaned_date.is_(None)).all()
            count = len(active)
            for load in active:
                load.cleaned_date = now
        else:
            count = session.query(InkLoad).count()
            session.query(InkLoad).delete()
        session.commit()
        return count
    finally:
        session.close()


def reset_ink_levels() -> int:
    """
    remaining_ml → bottle_size_ml, is_empty=False, is_archived=False.
    Gibt Anzahl betroffener Tinten zurück.
    """
    from database.models import Ink
    session = _STATE.session_factory()
    try:
        inks = session.query(Ink).all()
        for ink in inks:
            if ink.bottle_size_ml:
                ink.remaining_ml = ink.bottle_size_ml
            ink.is_empty = False
            ink.is_archived = False
        session.commit()
        return len(inks)
    finally:
        session.close()


def reset_pen_status() -> int:
    """
    Alle Füller auf availability_status='available' zurücksetzen.
    Service-Daten, Sperre und blocked_until werden gelöscht.
    Gibt Anzahl betroffener Füller zurück.
    """
    from database.models import Pen
    session = _STATE.session_factory()
    try:
        pens = session.query(Pen).all()
        for pen in pens:
            pen.availability_status = "available"
            pen.rotation_blocked = False
            pen.blocked_until = None
            pen.service_start_date = None
            pen.service_days = None
            pen.service_cost = None
            pen.service_currency = None
            pen.service_notes = None
        session.commit()
        return len(pens)
    finally:
        session.close()


def factory_reset_userdata() -> None:
    """
    Löscht alle Nutzerdaten: Füller, Tinten, Federn, Papier, InkLoads, Ausgaben.
    Systemregeln und AppSettings bleiben erhalten.
    NICHT rückgängig machbar – Backup vorher erstellen!
    """
    from database.models import InkLoad, Expense, OverrideLog, Pen, Ink, Nib, NibFormat, PenNibSetup, Paper, WishlistItem, WritingSample
    session = _STATE.session_factory()
    try:
        session.query(OverrideLog).delete()
        session.query(InkLoad).delete()
        session.query(Expense).delete()
        session.query(WishlistItem).delete()
        session.query(PenNibSetup).delete()

        # Bilddateien einsammeln, bevor die DB-Zeilen gelöscht werden.
        image_paths = []
        for model in (Pen, Ink, Paper, WritingSample):
            for obj in session.query(model).all():
                path = getattr(obj, "image_path", None)
                if path:
                    image_paths.append(Path(path))

        # FK-Referenzen lösen bevor Zeilen gelöscht werden
        for pen in session.query(Pen).all():
            pen.nib_id = None
            pen.fixed_ink_id = None
        session.flush()
        session.query(Pen).delete()
        session.query(Ink).delete()
        session.query(Nib).delete()
        session.query(NibFormat).delete()
        session.query(Paper).delete()
        session.commit()

        for path in image_paths:
            try:
                resolved = path.expanduser().resolve()
                data_root = _data_dir().resolve()
                if resolved.exists() and data_root in resolved.parents:
                    resolved.unlink()
            except Exception:
                pass
        images_root = _data_dir() / "images"
        for sub in ("pens", "inks", "papers"):
            folder = images_root / sub
            try:
                if folder.exists() and not any(folder.iterdir()):
                    folder.rmdir()
            except Exception:
                pass
        media_root = _data_dir() / "media"
        try:
            if media_root.exists() and not any(media_root.rglob("*")):
                media_root.rmdir()
        except Exception:
            pass
    finally:
        session.close()
