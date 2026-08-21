"""Ein Update-Archiv darf beim Entpacken nichts anrichten.

Die Signatur des Manifests deckt die Pruefsumme des Archivs ab - sie sagt aber
nichts darueber, was beim Entpacken passiert. Ein Archiv kann harmlos aussehen
und die Platte fuellen, oder Dateien ausserhalb des Zielordners anlegen.

Alle vier Programme der Suite fuehren diesen Test unter demselben Namen.
"""

from __future__ import annotations

import zipfile

import pytest

from updater.common import (
    MAX_UPDATE_COMPRESSION_RATIO,
    MAX_UPDATE_MEMBER_BYTES,
    MAX_ZIP_ENTRIES,
    safe_extract_zip,
)


def _archiv(pfad, eintraege: dict[str, bytes]):
    with zipfile.ZipFile(pfad, "w", zipfile.ZIP_DEFLATED) as z:
        for name, inhalt in eintraege.items():
            z.writestr(name, inhalt)
    return pfad


def test_ein_harmloses_archiv_wird_entpackt(tmp_path):
    quelle = _archiv(tmp_path / "gut.zip", {"a.txt": b"x", "unter/b.txt": b"y"})
    ziel = tmp_path / "ziel"
    safe_extract_zip(quelle, ziel)
    assert (ziel / "a.txt").read_bytes() == b"x"
    assert (ziel / "unter" / "b.txt").read_bytes() == b"y"


@pytest.mark.parametrize(
    "name",
    ["../ausbruch.txt", "unter/../../ausbruch.txt", "/absolut.txt", "C:/windows.txt"],
)
def test_pfad_traversal_wird_abgewiesen(tmp_path, name):
    quelle = _archiv(tmp_path / "boese.zip", {name: b"x"})
    with pytest.raises(ValueError):
        safe_extract_zip(quelle, tmp_path / "ziel")
    assert not (tmp_path / "ausbruch.txt").exists()


def test_ein_symlink_wird_abgewiesen(tmp_path):
    """Ein Symlink auf /etc/passwd macht aus einem Update einen Schreibzugriff
    an eine ganz andere Stelle."""
    quelle = tmp_path / "link.zip"
    with zipfile.ZipFile(quelle, "w") as z:
        eintrag = zipfile.ZipInfo("link")
        eintrag.external_attr = (0o120777 << 16)
        z.writestr(eintrag, "/etc/passwd")
    with pytest.raises(ValueError):
        safe_extract_zip(quelle, tmp_path / "ziel")


def test_eine_zip_bombe_wird_abgewiesen(tmp_path):
    """Stark komprimierte Nullen: klein im Archiv, riesig auf der Platte."""
    quelle = tmp_path / "bombe.zip"
    with zipfile.ZipFile(quelle, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.writestr("gross.bin", b"\0" * (MAX_UPDATE_COMPRESSION_RATIO * 4096))
    with pytest.raises(ValueError, match="Kompressionsrate"):
        safe_extract_zip(quelle, tmp_path / "ziel")


def test_zu_viele_eintraege_werden_abgewiesen(tmp_path, monkeypatch):
    """Sehr viele winzige Dateien kosten Zeit und Inodes, ohne die
    Groessengrenze zu reissen."""
    import updater.common as common

    monkeypatch.setattr(common, "MAX_ZIP_ENTRIES", 5)
    quelle = _archiv(tmp_path / "viele.zip", {f"d{i}.txt": b"x" for i in range(6)})
    with pytest.raises(ValueError, match="zu viele"):
        safe_extract_zip(quelle, tmp_path / "ziel")


def test_eine_uebergrosse_datei_wird_abgewiesen(tmp_path, monkeypatch):
    import updater.common as common

    monkeypatch.setattr(common, "MAX_UPDATE_MEMBER_BYTES", 10)
    quelle = _archiv(tmp_path / "gross.zip", {"a.txt": b"x" * 100})
    with pytest.raises(ValueError, match="zu gross"):
        safe_extract_zip(quelle, tmp_path / "ziel")


def test_die_grenzen_sind_gesetzt():
    """Ein versehentlich entfernter Grenzwert faellt sonst nicht auf."""
    assert MAX_ZIP_ENTRIES > 0
    assert MAX_UPDATE_MEMBER_BYTES > 0
    assert MAX_UPDATE_COMPRESSION_RATIO > 1
