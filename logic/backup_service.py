"""Vollständige, prüfbare Sicherung und Wiederherstellung der FPM-Nutzerdaten."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from app_info import APP_VERSION

BACKUP_FORMAT = 1
MANIFEST_NAME = "manifest.json"
DB_ARCHIVE_PATH = "database/fpm.db"


@dataclass(frozen=True)
class BackupResult:
    path: Path
    file_count: int
    size_bytes: int


@dataclass(frozen=True)
class RestoreResult:
    archive: Path
    restored_file_count: int
    database_path: Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sqlite_snapshot(source_path: Path, destination_path: Path) -> None:
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(f"file:{source_path}?mode=ro", uri=True) as source:
        with sqlite3.connect(destination_path) as destination:
            source.backup(destination)
    with sqlite3.connect(destination_path) as check:
        integrity = check.execute("PRAGMA integrity_check").fetchone()
        if not integrity or str(integrity[0]).lower() != "ok":
            raise ValueError(f"SQLite-Snapshot ist beschädigt: {integrity}")


def _skip_data_file(path: Path, *, data_dir: Path, db_path: Path, destination: Path) -> bool:
    resolved = path.resolve()
    if resolved in {db_path.resolve(), destination.resolve()}:
        return True
    relative = resolved.relative_to(data_dir.resolve())
    # Sicherungen nicht in neue Sicherungen verschachteln; Nutzerdaten und Caches bleiben enthalten.
    if relative.parts and relative.parts[0] in {"backups", "migration_backups"}:
        return True
    return path.suffix.lower() in {".fpmbackup", ".tmp"}


def create_full_backup(
    destination: str | Path,
    *,
    data_dir: str | Path | None = None,
    db_path: str | Path | None = None,
) -> BackupResult:
    """Erstellt ein Vollbackup mit SQLite-Snapshot, Medien, Cache und Konfiguration."""
    if data_dir is None or db_path is None:
        from database.db import get_data_dir, get_db_path

        data_dir = get_data_dir() if data_dir is None else data_dir
        db_path = get_db_path() if db_path is None else db_path

    destination = Path(destination).expanduser()
    if destination.suffix.lower() != ".fpmbackup":
        destination = destination.with_suffix(".fpmbackup")
    data_dir = Path(data_dir).expanduser()
    db_path = Path(db_path).expanduser()

    if not db_path.is_file():
        raise FileNotFoundError(f"Datenbank nicht gefunden: {db_path}")
    destination.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="fpm_backup_") as temp_name:
        temp_root = Path(temp_name)
        staged_db = temp_root / DB_ARCHIVE_PATH
        _sqlite_snapshot(db_path, staged_db)

        staged_files: dict[str, Path] = {DB_ARCHIVE_PATH: staged_db}
        if data_dir.exists():
            for source in sorted(data_dir.rglob("*")):
                if not source.is_file() or _skip_data_file(
                    source, data_dir=data_dir, db_path=db_path, destination=destination
                ):
                    continue
                relative = source.resolve().relative_to(data_dir.resolve()).as_posix()
                archive_name = f"data/{relative}"
                staged = temp_root / archive_name
                staged.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, staged)
                staged_files[archive_name] = staged

        manifest = {
            "format": BACKUP_FORMAT,
            "app_version": APP_VERSION,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "database": DB_ARCHIVE_PATH,
            "files": {
                name: {"sha256": _sha256(path), "size": path.stat().st_size}
                for name, path in sorted(staged_files.items())
            },
        }
        manifest_path = temp_root / MANIFEST_NAME
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

        temporary_archive = destination.with_name(destination.name + ".tmp")
        temporary_archive.unlink(missing_ok=True)
        with zipfile.ZipFile(temporary_archive, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(manifest_path, MANIFEST_NAME)
            for name, path in sorted(staged_files.items()):
                archive.write(path, name)
        temporary_archive.replace(destination)

    inspect_backup(destination)
    return BackupResult(destination, len(staged_files), destination.stat().st_size)


def _safe_member(name: str) -> bool:
    path = PurePosixPath(name)
    return not path.is_absolute() and ".." not in path.parts and bool(path.parts)


def inspect_backup(archive_path: str | Path) -> dict:
    """Validiert Aufbau, Pfade, Hashes und SQLite-Integrität eines Backups."""
    archive_path = Path(archive_path).expanduser()
    with zipfile.ZipFile(archive_path, "r") as archive:
        name_list = archive.namelist()
        names = set(name_list)
        if len(names) != len(name_list):
            raise ValueError("Backup enthält doppelte Dateinamen")
        if MANIFEST_NAME not in names:
            raise ValueError("Backup enthält kein manifest.json")
        if any(not _safe_member(name) for name in names):
            raise ValueError("Backup enthält einen unsicheren Dateipfad")
        manifest = json.loads(archive.read(MANIFEST_NAME).decode("utf-8"))
        if int(manifest.get("format", -1)) != BACKUP_FORMAT:
            raise ValueError("Nicht unterstütztes Backup-Format")
        files = manifest.get("files")
        if not isinstance(files, dict) or DB_ARCHIVE_PATH not in files:
            raise ValueError("Backup enthält keinen gültigen Datenbankeintrag")
        expected_names = set(files) | {MANIFEST_NAME}
        if names != expected_names:
            extras = sorted(names - expected_names)
            missing = sorted(expected_names - names)
            raise ValueError(f"Backup-Inhalt weicht vom Manifest ab: extra={extras}, fehlt={missing}")
        for name, metadata in files.items():
            if name not in names or not _safe_member(name) or not isinstance(metadata, dict):
                raise ValueError(f"Backup-Datei fehlt oder ist unsicher: {name}")
            payload = archive.read(name)
            if len(payload) != int(metadata.get("size", -1)):
                raise ValueError(f"Dateigröße stimmt nicht: {name}")
            digest = hashlib.sha256(payload).hexdigest()
            if digest != metadata.get("sha256"):
                raise ValueError(f"Prüfsumme stimmt nicht: {name}")

        with tempfile.TemporaryDirectory(prefix="fpm_backup_check_") as temp_name:
            db_copy = Path(temp_name) / "fpm.db"
            db_copy.write_bytes(archive.read(DB_ARCHIVE_PATH))
            with sqlite3.connect(db_copy) as connection:
                integrity = connection.execute("PRAGMA integrity_check").fetchone()
                if not integrity or str(integrity[0]).lower() != "ok":
                    raise ValueError(f"Datenbank im Backup ist beschädigt: {integrity}")
                violations = connection.execute("PRAGMA foreign_key_check").fetchall()
                if violations:
                    raise ValueError(
                        f"Datenbank im Backup enthält {len(violations)} ungültige Fremdschlüssel"
                    )
    return manifest


def restore_full_backup(
    archive_path: str | Path,
    *,
    data_dir: str | Path | None = None,
    db_path: str | Path | None = None,
) -> RestoreResult:
    """Stellt ein validiertes Vollbackup wieder her.

    ``backups/`` und ``migration_backups/`` des Zielsystems bleiben erhalten,
    damit die Rückfallsicherung nicht durch die Wiederherstellung verschwindet.
    """
    if data_dir is None or db_path is None:
        from database.db import get_data_dir, get_db_path

        data_dir = get_data_dir() if data_dir is None else data_dir
        db_path = get_db_path() if db_path is None else db_path

    archive_path = Path(archive_path).expanduser().resolve()
    data_dir = Path(data_dir).expanduser().resolve()
    db_path = Path(db_path).expanduser().resolve()
    manifest = inspect_backup(archive_path)

    with tempfile.TemporaryDirectory(prefix="fpm_restore_") as temp_name:
        temp_root = Path(temp_name)
        with zipfile.ZipFile(archive_path, "r") as archive:
            for name in manifest["files"]:
                target = temp_root / PurePosixPath(name)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(name))

        staged_db = temp_root / DB_ARCHIVE_PATH
        data_dir.mkdir(parents=True, exist_ok=True)

        # Vorhandene aktive Nutzerdaten entfernen, Rückfall-Backups aber bewahren.
        for child in list(data_dir.iterdir()):
            if child.name in {"backups", "migration_backups"}:
                continue
            if archive_path == child.resolve():
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink(missing_ok=True)

        staged_data = temp_root / "data"
        restored_files = 1
        if staged_data.exists():
            for source in sorted(staged_data.rglob("*")):
                if not source.is_file():
                    continue
                relative = source.relative_to(staged_data)
                target = data_dir / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                restored_files += 1

        db_path.parent.mkdir(parents=True, exist_ok=True)
        replacement = db_path.with_name(db_path.name + ".restore_tmp")
        shutil.copy2(staged_db, replacement)
        os.replace(replacement, db_path)

        # Der DB-Pfad des alten Rechners darf den aktuellen Zielpfad nicht überschreiben.
        config_path = data_dir / "config.json"
        try:
            config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
        except (OSError, json.JSONDecodeError):
            config = {}
        config["db_path"] = str(db_path)
        config_path.write_text(
            json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    return RestoreResult(archive_path, restored_files, db_path)
