"""v0.2.87: Ein fehlgeschlagener Medien-Import darf niemals Daten zerstören.

Hintergrund (Release-Analyse): In `pen_widget._add/_edit/_duplicate` und
`writing_samples_widget._add/_edit` lief `import_*_image()` **innerhalb** der
offenen Transaktion vor dem Commit. Jede Exception (Netzfehler, Timeout,
"Bilddatei ist zu groß", fehlende Schreibrechte) landete im generischen
`except` -> Rollback bzw. kein Commit. Ergebnis: Der Nutzer verlor den
komplett eingetippten Füller bzw. die Schreibprobe, weil ein *kosmetischer*
Bild-Import fehlschlug.

Hier wird zweierlei geprüft:
1. **Real:** Der Media-Service wirft in genau diesen Fällen tatsächlich
   (sonst wäre der Fix ein Phantom-Fix).
2. **Statisch:** Die Aufrufer fangen ab, behalten den Rohpfad und warnen erst
   nach erfolgreichem Commit.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from logic.media_storage_service import (  # noqa: E402
    MAX_MEDIA_BYTES,
    import_media_asset,
    import_pen_image,
    is_inside,
    is_managed_media_path,
    safe_slug,
)


def _src(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _method_body(src: str, signature: str) -> str:
    """Body genau einer Methode – exakte Signatur, damit nicht z. B.
    ``_add_writing_sample_for_pen`` statt ``_add`` getroffen wird."""
    assert signature in src, signature
    return src.split(signature, 1)[1].split("\n    def ", 1)[0]


# ── 1. Der Service wirft wirklich (Fix ist kein Phantom) ─────────────
def test_oversized_download_raises(tmp_path, monkeypatch):
    import logic.media_storage_service as mss

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self, n):
            return b"x" * (MAX_MEDIA_BYTES + 1)

    monkeypatch.setattr(mss.urllib.request, "urlopen", lambda *a, **k: _Resp())
    try:
        import_pen_image(tmp_path, "https://example.test/big.jpg", pen_id=1, brand="B", model="M")
    except ValueError as exc:
        assert "gro" in str(exc).lower()
    else:
        raise AssertionError("Übergroßer Download muss eine Exception auslösen")


def test_empty_download_raises(tmp_path, monkeypatch):
    import logic.media_storage_service as mss

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self, n):
            return b""

    monkeypatch.setattr(mss.urllib.request, "urlopen", lambda *a, **k: _Resp())
    try:
        import_pen_image(tmp_path, "https://example.test/empty.jpg", pen_id=1, brand="B", model="M")
    except ValueError:
        pass
    else:
        raise AssertionError("Leerer Download muss eine Exception auslösen")


def test_network_error_propagates(tmp_path, monkeypatch):
    import logic.media_storage_service as mss

    def _boom(*a, **k):
        raise OSError("network unreachable")

    monkeypatch.setattr(mss.urllib.request, "urlopen", _boom)
    try:
        import_pen_image(tmp_path, "https://example.test/x.jpg", pen_id=1, brand="B", model="M")
    except OSError:
        pass
    else:
        raise AssertionError("Netzfehler muss eine Exception auslösen")


def test_missing_local_file_is_not_fatal_and_keeps_raw_path(tmp_path):
    """Nicht existierende lokale Pfade bleiben erhalten statt zu werfen."""
    result = import_media_asset(
        tmp_path, "/nicht/vorhanden/bild.jpg",
        pen_id=1, brand="B", model="M", kind="images",
    )
    assert result is not None and result.copied is False
    assert str(result.target).endswith("bild.jpg")


def test_local_copy_lands_in_managed_media_tree(tmp_path):
    src = tmp_path / "foto.png"
    src.write_bytes(b"\x89PNG\r\n\x1a\n")
    out = import_pen_image(tmp_path, src, pen_id=7, brand="Pelikan", model="M800")
    assert out and is_managed_media_path(out, tmp_path)
    assert is_inside(Path(out), tmp_path / "media")
    assert "pelikan" in out.lower() and "m800" in out.lower()


# ── 2. Slug/Containment bleiben ausbruchssicher ──────────────────────
def test_slug_and_containment_resist_traversal():
    assert safe_slug("../../etc") == "etc"
    assert safe_slug("...") == "item"
    assert safe_slug("") == "item"
    assert is_inside(Path("/tmp/root/a"), Path("/tmp/root"))
    assert not is_inside(Path("/tmp/root/../evil"), Path("/tmp/root"))


# ── 3. Aufrufer fangen ab, behalten Rohpfad, warnen nach Commit ──────
def test_pen_widget_media_import_is_non_fatal():
    src = _src("ui/pen_widget.py")
    store = src.split("def _store_pen_image_if_needed")[1].split("\n    def ")[0]
    assert "try:" in store and "except Exception" in store
    assert "_last_media_warning" in store
    # Rohpfad bleibt: image_path wird nur bei Erfolg überschrieben
    assert "if imported:" in store
    assert "_warn_media_import_failed" in src
    # Warnung erst NACH dem Commit
    # Genau die drei Methoden, die Bilder importieren – und nur diese.
    importing = ("def _add(self):", "def _edit_pen_by_id(self, pen_id: int):", "def _copy_pen(self):")
    for sig in importing:
        body = _method_body(src, sig)
        assert "_store_pen_image_if_needed(pen)" in body, sig
        assert "_warn_media_import_failed()" in body, sig
        assert body.index("session.commit()") < body.index("_warn_media_import_failed()"), sig
    # Keine Warn-Aufrufe in Methoden ohne Import (Rauschen vermeiden).
    warn_count = src.count("self._warn_media_import_failed()")
    assert warn_count == len(importing), warn_count


def test_writing_samples_media_import_is_non_fatal():
    src = _src("ui/writing_samples_widget.py")
    store = src.split("def _store_sample_image_if_needed")[1].split("\n    def ")[0]
    assert "try:" in store and "except Exception" in store
    assert "_last_media_warning" in store
    for sig in ("def _add(self) -> None:", "def _edit(self) -> None:"):
        body = _method_body(src, sig)
        assert "_warn_media_import_failed()" in body, sig
        assert body.index("session.commit()") < body.index("_warn_media_import_failed()")


def test_pen_widget_add_rolls_back_on_error():
    """Vorher fehlte im _add-Fehlerpfad ein explizites rollback()."""
    src = _src("ui/pen_widget.py")
    add_body = _method_body(src, "def _add(self):")
    assert "session.rollback()" in add_body


def test_media_warning_keys_exist_in_all_languages():
    import json

    for lang in ("de", "en", "fr"):
        data = json.loads((ROOT / "i18n" / f"{lang}.json").read_text(encoding="utf-8"))
        assert "media" in data
        assert data["media"]["import_failed_title"].strip()
        body = data["media"]["import_failed_body"]
        assert "{error}" in body
