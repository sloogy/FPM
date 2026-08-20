"""v0.3.01: Verhaltenstests für den Updater (Enterprise-Audit P1 Coverage).

Testet die sicherheits- und korrektheitskritischen Pfade ohne Netzwerk:
Manifest-Parsing, SemVer-Vergleich, ZipSlip-Schutz, Staging-Versionswahl
(inkl. 0.2.9 < 0.2.10), Exclude-Semantik von remove/copy sowie die
Ergebnis-Persistenz. ``fetch_manifest``/``download_file`` laufen gegen
gemockte, zentral abgesicherte HTTP-Antworten.
"""
from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pytest

from updater import common
from updater import apply_update


# ── Manifest-Parsing ────────────────────────────────────────────────────────

def test_parse_manifest_full_and_defaults():
    m = common.parse_manifest({
        "version": " 1.2.3 ",
        "release_tag": "v1.2.3",
        "assets": {
            "windows-portable": {"url": "https://x/w.zip", "sha256": "ABC", "type": "portable"},
            "linux-portable": {"url": "https://x/l.zip"},
            "kaputt": "kein-dict",
            "leer": {"url": "   "},
        },
    })
    assert m.version == "1.2.3"
    assert m.release_tag == "v1.2.3"
    assert m.channel == "stable"
    assert set(m.assets) == {"windows-portable", "linux-portable"}
    assert m.assets["windows-portable"].sha256 == "abc"  # normalisiert lowercase
    assert m.assets["linux-portable"].asset_type == "portable"


def test_parse_manifest_tolerates_missing_fields():
    m = common.parse_manifest({})
    assert m.version == "0.0.0"
    assert m.assets == {}


def test_fetch_manifest_uses_central_guard_and_validates(monkeypatch):
    class FakeResp:
        def __init__(self, payload):
            self.payload = payload
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self, _size):
            return json.dumps(self.payload).encode("utf-8")

    calls = {}
    def fake_open(url, *, timeout_s, headers):
        calls.update(url=url, timeout=timeout_s, headers=headers)
        return FakeResp({"version": "9.9.9", "assets": {}})
    monkeypatch.setattr(common, "open_public_http_url", fake_open)
    m = common.fetch_manifest("https://example.invalid/latest.json", timeout_s=5)
    assert m.version == "9.9.9"
    assert calls["url"] == "https://example.invalid/latest.json"
    assert calls["timeout"] == 5

    monkeypatch.setattr(
        common, "open_public_http_url",
        lambda *a, **k: FakeResp(["kein", "dict"]),
    )
    with pytest.raises(ValueError):
        common.fetch_manifest("https://example.invalid/latest.json")


# ── SemVer-Vergleich ────────────────────────────────────────────────────────

def test_is_newer_semver_semantics():
    assert common.is_newer("0.3.1", "0.3.0") is True
    assert common.is_newer("0.3.0", "0.3.0") is False
    assert common.is_newer("0.2.9", "0.2.10") is False   # numerisch, nicht lexikalisch
    assert common.is_newer("0.2.10", "0.2.9") is True
    assert common.is_newer("1.0.0", "1.0.0rc1") is True  # Release > RC


def test_is_newer_is_conservative_on_garbage():
    # Nicht parsebare Versionen dürfen NIE ein "Update" signalisieren.
    assert common.is_newer("kaputt", "0.3.0") is False
    assert common.is_newer("0.3.0", "kaputt") is False


# ── Asset-Auswahl & Typen ───────────────────────────────────────────────────

def test_preferred_asset_keys_platform_priority():
    keys = common.preferred_asset_keys("windows-portable")
    assert keys[0] == "windows-portable"
    assert all(isinstance(k, str) and k for k in keys)


def test_asset_is_zip_by_suffix_and_type():
    assert common.asset_is_zip("https://x/a.zip") is True
    assert common.asset_is_zip("https://x/a.exe") is False
    assert common.asset_is_zip("https://x/a.exe", asset_type="portable-zip") is True


# ── Hash & sichere Extraktion ───────────────────────────────────────────────

def test_sha256_file_matches_known_vector(tmp_path):
    f = tmp_path / "x.bin"
    f.write_bytes(b"abc")
    assert common.sha256_file(f) == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def _zip_with(entries) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in entries:
            z.writestr(name, data)
    return buf.getvalue()


def test_safe_extract_zip_blocks_zipslip(tmp_path):
    evil = tmp_path / "evil.zip"
    evil.write_bytes(_zip_with([
        ("gut/datei.txt", "ok"),
        ("../ausbruch.txt", "böse"),
        ("/absolut.txt", "böse"),
        ("a/../../auch_boese.txt", "böse"),
    ]))
    dest = tmp_path / "out"
    with pytest.raises(ValueError, match="Unsicherer Pfad"):
        common.safe_extract_zip(evil, dest)
    assert not dest.exists()
    assert not (tmp_path / "ausbruch.txt").exists()


def test_find_staged_root_unwraps_single_dir(tmp_path):
    staging = tmp_path / "staging"
    inner = staging / "FPM-1.0"
    inner.mkdir(parents=True)
    (inner / "main.py").write_text("x", encoding="utf-8")
    assert common.find_staged_root(staging) == inner
    # Mit Datei auf oberster Ebene bleibt die oberste Ebene das Root.
    (staging / "direkt.txt").write_text("x", encoding="utf-8")
    assert common.find_staged_root(staging) == staging


# ── Staging-Versionswahl (apply_update) ─────────────────────────────────────

def test_latest_staged_version_numeric_order(tmp_path, monkeypatch):
    updates = tmp_path / "updates"
    for v in ("0.2.9", "0.2.10", "0.2.2"):
        d = updates / "staging" / v
        d.mkdir(parents=True)
        (d / "marker.txt").write_text("x", encoding="utf-8")
    monkeypatch.setattr(common, "updates_dir", lambda: updates)
    monkeypatch.setattr(apply_update, "updates_dir", lambda: updates, raising=False)
    assert apply_update.latest_staged_version() == "0.2.10"


def test_read_marker_roundtrip_and_missing(tmp_path):
    staging = tmp_path / "s"
    staging.mkdir()
    assert apply_update.read_marker(staging) == {}
    (staging / "_update_marker.json").write_text(
        json.dumps({"version": "1.2.3"}), encoding="utf-8"
    )
    assert apply_update.read_marker(staging)["version"] == "1.2.3"


# ── remove/copy mit Exclude-Semantik ────────────────────────────────────────

def _tree(base: Path, spec: dict) -> None:
    for name, content in spec.items():
        p = base / name
        if isinstance(content, dict):
            p.mkdir(parents=True, exist_ok=True)
            _tree(p, content)
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")


def test_remove_paths_keeps_excluded(tmp_path):
    target = tmp_path / "app"
    _tree(target, {
        "main.py": "alt",
        "userdata": {"db.sqlite": "wichtig"},
        "logs": {"a.log": "x"},
    })
    apply_update.remove_paths(target, exclude=("userdata",))
    assert (target / "userdata" / "db.sqlite").read_text(encoding="utf-8") == "wichtig"
    assert not (target / "main.py").exists()
    assert not (target / "logs").exists()


def test_copy_new_skips_excluded_sources(tmp_path):
    src = tmp_path / "neu"
    dst = tmp_path / "app"
    dst.mkdir()
    _tree(src, {
        "main.py": "neu",
        "userdata": {"soll_nicht_kommen.txt": "x"},
        "ui": {"w.py": "code"},
    })
    apply_update.copy_new(src, dst, exclude=("userdata",))
    assert (dst / "main.py").read_text(encoding="utf-8") == "neu"
    assert (dst / "ui" / "w.py").exists()
    assert not (dst / "userdata").exists()


# ── Ergebnis-Persistenz ─────────────────────────────────────────────────────

def test_check_result_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(common, "updates_dir", lambda: tmp_path)
    common.write_check_result({"available": True, "version": "9.9.9"})
    data = common.read_check_result()
    assert data["available"] is True and data["version"] == "9.9.9"
    common.clear_check_result()
    assert common.read_check_result() == {}


def test_read_check_result_survives_corrupt_file(tmp_path, monkeypatch):
    monkeypatch.setattr(common, "updates_dir", lambda: tmp_path)
    common.check_result_path().parent.mkdir(parents=True, exist_ok=True)
    common.check_result_path().write_text("{kaputt", encoding="utf-8")
    assert common.read_check_result() == {}
