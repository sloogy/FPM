"""v0.2.88: Umsetzung der Restrisiken aus der kritischen Release-Analyse.

Geprüft werden – soweit ohne Qt möglich – reale Verhaltensweisen, nicht nur
Textmuster:

1. Magic-Bytes: HTML-Fehlerseiten unter ``.jpg`` werden abgelehnt.
2. Redirect-/Scheme-Schutz: nur http/https, auch nach Weiterleitung.
3. Timeout: von 15 s auf 8 s gesenkt und durchgereicht.
4. Endungskorrektur nach dem tatsächlich erkannten Format.
5. Worker-Auslagerung und Temp-Aufräumung (statisch, GUI nicht startbar).
"""
import sys
import socket
import urllib.error

import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import logic.media_storage_service as mss  # noqa: E402
import logic.network_security as network_security  # noqa: E402
from logic.media_storage_service import (  # noqa: E402
    ALLOWED_DOWNLOAD_SCHEMES,
    DOWNLOAD_TIMEOUT_S,
    detect_image_suffix,
    download_image_bytes,
    import_pen_image,
)

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 40
JPG = b"\xff\xd8\xff\xe0" + b"0" * 40
HTML = b"<!DOCTYPE html><html><body>404 Not Found</body></html>"


@pytest.fixture(autouse=True)
def _public_dns(monkeypatch):
    monkeypatch.setattr(
        network_security.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))
        ],
    )



def _src(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


class _Resp:
    def __init__(self, payload: bytes, url: str = "https://example.test/final"):
        self._payload = payload
        self._offset = 0
        self._url = url
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()
        return False

    def geturl(self):
        return self._url

    def close(self):
        self.closed = True

    def read(self, n):
        if self.closed:
            return b""
        part = self._payload[self._offset:self._offset + n]
        self._offset += len(part)
        return part


def _fake_opener(payload: bytes, recorder: dict | None = None):
    class _O:
        def open(self, request, timeout=None):
            if recorder is not None:
                recorder["timeout"] = timeout
                recorder["url"] = request.full_url
            return _Resp(payload)

    return _O()


# ── 1. Magic-Bytes ───────────────────────────────────────────────────
def test_detect_image_suffix_recognises_formats():
    assert detect_image_suffix(PNG) == ".png"
    assert detect_image_suffix(JPG) == ".jpg"
    assert detect_image_suffix(b"GIF89a" + b"0" * 10) == ".gif"
    assert detect_image_suffix(b"RIFF1234WEBPxxxx") == ".webp"
    assert detect_image_suffix(b"BM" + b"0" * 10) == ".bmp"
    assert detect_image_suffix(HTML) is None
    assert detect_image_suffix(b"") is None


def test_html_error_page_is_rejected_not_saved(tmp_path):
    original = mss._opener
    mss._opener = _fake_opener(HTML)
    try:
        import_pen_image(tmp_path, "https://example.test/bild.jpg", pen_id=1, brand="B", model="M")
    except ValueError as exc:
        assert "bildformat" in str(exc).lower()
    else:
        raise AssertionError("HTML-Seite darf nicht als Bild gespeichert werden")
    finally:
        mss._opener = original
    media = tmp_path / "media"
    assert not media.exists() or not list(media.rglob("*.jpg"))


def test_wrong_extension_is_corrected_to_detected_format(tmp_path):
    original = mss._opener
    mss._opener = _fake_opener(PNG)
    try:
        out = import_pen_image(tmp_path, "https://example.test/foto.jpg", pen_id=3, brand="Lamy", model="2000")
    finally:
        mss._opener = original
    assert out is not None and out.endswith(".png"), out
    assert Path(out).read_bytes() == PNG


def test_jpeg_extension_stays_jpeg(tmp_path):
    original = mss._opener
    mss._opener = _fake_opener(JPG)
    try:
        out = import_pen_image(tmp_path, "https://example.test/foto.jpeg", pen_id=4, brand="B", model="M")
    finally:
        mss._opener = original
    assert out.endswith(".jpeg"), out


# ── 2. Scheme-/Redirect-Schutz ───────────────────────────────────────
def test_non_http_schemes_are_rejected():
    for url in ("file:///etc/passwd", "ftp://example.test/x.jpg", "data:image/png;base64,AAAA"):
        try:
            download_image_bytes(url)
        except ValueError as exc:
            assert "http" in str(exc).lower()
        else:
            raise AssertionError(f"{url} muss abgelehnt werden")


def test_allowed_schemes_are_exactly_http_and_https():
    assert set(ALLOWED_DOWNLOAD_SCHEMES) == {"http", "https"}


def test_redirect_handler_blocks_non_http_targets():
    handler = mss._SafeRedirectHandler()
    try:
        handler.redirect_request(None, None, 302, "Found", {}, "ftp://evil.test/x")
    except urllib.error.HTTPError as exc:
        assert "weiterleit" in str(exc).lower()
    else:
        raise AssertionError("Redirect nach ftp:// muss abgelehnt werden")


# ── 3. Timeout ───────────────────────────────────────────────────────
def test_timeout_default_lowered_and_passed_through():
    assert DOWNLOAD_TIMEOUT_S == 8
    rec: dict = {}
    original = mss._opener
    mss._opener = _fake_opener(PNG, rec)
    try:
        download_image_bytes("https://example.test/a.png")
        assert rec["timeout"] == 8
        download_image_bytes("https://example.test/a.png", timeout_s=2)
        assert rec["timeout"] == 2
    finally:
        mss._opener = original


def test_size_limit_checked_before_writing(tmp_path):
    original = mss._opener
    mss._opener = _fake_opener(PNG[:8] + b"x" * (mss.MAX_MEDIA_BYTES + 8))
    try:
        import_pen_image(tmp_path, "https://example.test/big.png", pen_id=1, brand="B", model="M")
        raise AssertionError("Übergroßer Download muss abgelehnt werden")
    except ValueError:
        pass
    finally:
        mss._opener = original
    if (tmp_path / "media").exists():
        assert not list((tmp_path / "media").rglob("*.png"))


def test_network_error_still_propagates(tmp_path):
    class _O:
        def open(self, request, timeout=None):
            raise urllib.error.URLError("unreachable")

    original = mss._opener
    mss._opener = _O()
    try:
        import_pen_image(tmp_path, "https://example.test/x.png", pen_id=1, brand="B", model="M")
    except Exception as exc:
        assert "unreachable" in str(exc).lower() or isinstance(exc, urllib.error.URLError)
    else:
        raise AssertionError("Netzfehler muss durchschlagen (Aufrufer fängt ab)")
    finally:
        mss._opener = original


# ── 4. Worker-Auslagerung (statisch – Qt nicht startbar) ─────────────
def test_download_worker_module_exists_and_is_qt_only():
    src = _src("ui/media_download.py")
    assert "class _DownloadWorker" in src and "QThread" in src
    assert "moveToThread" in src
    assert "QProgressDialog" in src and "canceled.connect" in src
    # Netz-/Prüflogik bleibt im Service, nicht in der Qt-Hülle
    assert "urlopen" not in src and "_opener" not in src
    assert "ImageDownloadOperation" in src and "worker.cancel()" in src


def test_widgets_prefetch_urls_off_the_gui_thread():
    for rel in ("ui/pen_widget.py", "ui/writing_samples_widget.py"):
        src = _src(rel)
        assert "_prefetch_remote_image" in src, rel
        assert "from ui.media_download import download_image_to" in src, rel
        assert "_cleanup_temp_media" in src, rel
        # Aufräumen hängt am Nach-Commit-Pfad
        warn = src.split("def _warn_media_import_failed")[1].split("\n    def ")[0]
        assert "_cleanup_temp_media()" in warn, rel


def test_local_paths_bypass_the_downloader(tmp_path):
    """Nicht-URLs dürfen keinen Netzpfad anstoßen (Regressionsschutz)."""
    src = _src("ui/pen_widget.py")
    body = src.split("def _prefetch_remote_image")[1].split("\n    def ")[0]
    assert "startswith(('http://', 'https://'))" in body
    assert "return raw" in body


# ── 5. Reset räumt leere Medienordner auf ────────────────────────────
def test_reset_cleans_empty_media_tree_recursively():
    src = _src("database/db.py")
    block = src.split('media_root = _data_dir() / "media"')[1][:900]
    assert "rglob" in block and "is_dir()" in block
    assert "reverse=True" in block   # tiefste Ordner zuerst
    assert "folder.rmdir()" in block
