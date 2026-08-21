"""Automatische Sicherungen wachsen nicht unbegrenzt mit.

Vor jeder Schemaaenderung legt FPM eine Sicherheitskopie an. Die entsteht bei
jedem Update und ist so gross wie die Datenbank selbst - bei einer grossen
Sammlung summiert sich das ueber die Jahre.

Aufgeraeumt wird ausschliesslich in ``migration_backups``: Was der Nutzer ueber
den Sicherungsdialog an einen eigenen Ort gelegt hat, wird nie angefasst.
"""

from __future__ import annotations

import pytest

from database.db import (
    MIGRATION_BACKUPS_AUFBEWAHREN,
    _alte_migrationsbackups_entfernen,
)


def _backups(ordner, anzahl: int, muster: str = "sammlung_before_v{i:02d}_20260101_000000.db"):
    for i in range(anzahl):
        (ordner / muster.format(i=i)).write_text(f"stand {i}", encoding="utf-8")


def test_unterhalb_der_grenze_bleibt_alles(tmp_path):
    _backups(tmp_path, 3)
    _alte_migrationsbackups_entfernen(tmp_path)
    assert len(list(tmp_path.glob("*_before_*"))) == 3


def test_oberhalb_der_grenze_bleiben_die_juengsten(tmp_path):
    _backups(tmp_path, MIGRATION_BACKUPS_AUFBEWAHREN + 5)
    _alte_migrationsbackups_entfernen(tmp_path)

    verblieben = sorted(p.name for p in tmp_path.glob("*_before_*"))
    assert len(verblieben) == MIGRATION_BACKUPS_AUFBEWAHREN
    # Die juengsten tragen die hoechsten Nummern.
    assert verblieben[-1].startswith("sammlung_before_v14")


def test_fremde_dateien_bleiben_unangetastet(tmp_path):
    """Der wichtige Teil: nur die selbst erzeugten Sicherungen."""
    _backups(tmp_path, MIGRATION_BACKUPS_AUFBEWAHREN + 5)
    eigene = tmp_path / "mein_wichtiges_backup.db"
    eigene.write_text("von Hand gesichert", encoding="utf-8")
    auch = tmp_path / "sammlung.db"
    auch.write_text("die Datenbank selbst", encoding="utf-8")

    _alte_migrationsbackups_entfernen(tmp_path)

    assert eigene.is_file()
    assert auch.is_file()


def test_ein_leerer_ordner_ist_kein_fehler(tmp_path):
    _alte_migrationsbackups_entfernen(tmp_path)


def test_unterordner_werden_nicht_geloescht(tmp_path):
    (tmp_path / "sammlung_before_alt").mkdir()
    _backups(tmp_path, MIGRATION_BACKUPS_AUFBEWAHREN + 3)
    _alte_migrationsbackups_entfernen(tmp_path)
    assert (tmp_path / "sammlung_before_alt").is_dir()


def test_die_grenze_ist_gesetzt():
    assert MIGRATION_BACKUPS_AUFBEWAHREN > 0
