"""Eine unlesbare config.json wird gerettet, nicht ueberschrieben.

In ``config.json`` steht der Datenbankpfad. Bis Loop 21 wurde eine kaputte
Datei stumm verworfen: FPM oeffnete die leere Standarddatenbank - das sieht
wie ein Totalverlust aus - und das naechste Speichern ueberschrieb die
kaputte Datei endgueltig. Dieselben Faelle pruefen BudgetManager und
LifePlanner unter demselben Dateinamen.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

import database.db as db


@pytest.fixture()
def datenordner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(db, "_data_dir", lambda: tmp_path)
    return tmp_path


def _kaputte(ordner: Path) -> list[Path]:
    return sorted(ordner.glob("config.json.kaputt-*"))


def test_unlesbare_datei_wird_beiseitegelegt(datenordner: Path) -> None:
    ziel = datenordner / "config.json"
    ziel.write_text('{"db_path": ', encoding="utf-8")

    assert db._load_config() == {}

    assert not ziel.exists(), "die kaputte Datei darf nicht liegen bleiben"
    gerettet = _kaputte(datenordner)
    assert len(gerettet) == 1
    assert gerettet[0].read_text(encoding="utf-8") == '{"db_path": '


def test_falsches_format_wird_beiseitegelegt(datenordner: Path) -> None:
    """Gueltiges JSON, aber kein Objekt - fuehrte spaeter zu Folgefehlern."""
    (datenordner / "config.json").write_text("[1, 2]", encoding="utf-8")

    assert db._load_config() == {}
    assert len(_kaputte(datenordner)) == 1


def test_zwei_fehlschlaege_in_derselben_sekunde(datenordner: Path) -> None:
    """Beide Fassungen bleiben erhalten - der Zeitstempel allein reicht nicht."""
    ziel = datenordner / "config.json"
    for inhalt in ("{erster", "{zweiter"):
        ziel.write_text(inhalt, encoding="utf-8")
        db._load_config()

    gerettet = _kaputte(datenordner)
    assert len(gerettet) == 2
    assert {p.read_text(encoding="utf-8") for p in gerettet} == {"{erster", "{zweiter"}


def test_beiseitegelegte_fassungen_wachsen_nicht_unbegrenzt(
    datenordner: Path,
) -> None:
    ziel = datenordner / "config.json"
    for _ in range(15):
        ziel.write_text("{kaputt", encoding="utf-8")
        db._load_config()

    assert len(_kaputte(datenordner)) == 10


def test_heile_datei_bleibt_unangetastet(datenordner: Path) -> None:
    ziel = datenordner / "config.json"
    ziel.write_text('{"db_path": "/pfad/zur.db"}', encoding="utf-8")

    assert db._load_config() == {"db_path": "/pfad/zur.db"}
    assert ziel.exists()
    assert not _kaputte(datenordner)


def test_speichern_ist_atomar_und_nur_fuer_den_besitzer_lesbar(
    datenordner: Path,
) -> None:
    db._save_config({"db_path": "/pfad/zur.db"})

    ziel = datenordner / "config.json"
    assert json.loads(ziel.read_text(encoding="utf-8")) == {"db_path": "/pfad/zur.db"}
    assert not list(datenordner.glob("config.json.tmp-*")), "kein Rest der Zwischendatei"
    if os.name == "posix":
        assert ziel.stat().st_mode & 0o777 == 0o600


def test_abgebrochenes_speichern_laesst_den_alten_stand_stehen(
    datenordner: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ohne atomares Schreiben stand hier die halbe Datei."""
    ziel = datenordner / "config.json"
    db._save_config({"db_path": "/alt.db"})

    def bricht_ab(self, target):  # type: ignore[no-untyped-def]
        raise OSError("Kein Platz")

    monkeypatch.setattr(Path, "replace", bricht_ab)
    with pytest.raises(OSError):
        db._save_config({"db_path": "/neu.db"})

    assert json.loads(ziel.read_text(encoding="utf-8")) == {"db_path": "/alt.db"}
    assert not list(datenordner.glob("config.json.tmp-*"))
