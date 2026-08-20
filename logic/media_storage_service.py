"""Zentrale Medienablage für Füller, Bilder und Schreibproben.

Bilder bleiben als Dateien im Datenverzeichnis neben der SQLite-Datenbank. Die
DB speichert nur den Pfad. Neue Imports werden pro Füller sortiert, damit beim
Backup/Umzug alles an einem Ort liegt und Schreibproben später eindeutig zum
Füller zurückverfolgbar sind.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re
import shutil
import urllib.error
import urllib.parse
import urllib.request
import unicodedata
from typing import Literal
import threading

from logic.network_security import (
    SafePublicRedirectHandler,
    build_public_http_opener,
    validate_connected_peer,
    validate_public_http_url,
)

SUPPORTED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}
MAX_MEDIA_BYTES = 15 * 1024 * 1024
DOWNLOAD_TIMEOUT_S = 8            # v0.2.88: war 15 s; blockiert die UI kürzer
ALLOWED_DOWNLOAD_SCHEMES = ("http", "https")

# v0.2.88: Magic-Bytes je Bildformat. Eine HTML-Fehlerseite, die unter ".jpg"
# ausgeliefert wird, landet damit nicht mehr als vermeintliches Bild im
# Medienordner. Bewusst byte-basiert statt Content-Type-Header: Header lügen,
# der Dateianfang nicht.
_IMAGE_MAGIC: tuple[tuple[bytes, str], ...] = (
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"\xff\xd8\xff", ".jpg"),
    (b"GIF87a", ".gif"),
    (b"GIF89a", ".gif"),
    (b"BM", ".bmp"),
    (b"II*\x00", ".tif"),
    (b"MM\x00*", ".tif"),
)


def detect_image_suffix(data: bytes) -> str | None:
    """Erkennt das Bildformat am Dateianfang. ``None`` = kein bekanntes Bild."""
    if not data:
        return None
    for magic, suffix in _IMAGE_MAGIC:
        if data.startswith(magic):
            return suffix
    # RIFF....WEBP
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    return None


class _SafeRedirectHandler(SafePublicRedirectHandler):
    """Backward-compatible name for the central public redirect guard."""


_opener = build_public_http_opener()


class DownloadCancelledError(ValueError):
    """Raised when a user cancels an active image download."""


class ImageDownloadOperation:
    """Thread-safe, cooperatively abortable image download operation."""

    def __init__(self, url: str, *, timeout_s: int = DOWNLOAD_TIMEOUT_S):
        self.url = str(url or "").strip()
        self.timeout_s = int(timeout_s)
        self._cancelled = threading.Event()
        self._response_lock = threading.Lock()
        self._response = None

    def cancel(self) -> None:
        self._cancelled.set()
        with self._response_lock:
            response = self._response
        if response is not None:
            try:
                response.close()
            except (OSError, ValueError):
                pass

    def download(self) -> tuple[bytes, str]:
        validate_public_http_url(self.url)
        request = urllib.request.Request(
            self.url,
            headers={"User-Agent": "FountainPenManager/media-import"},
        )
        response = None
        try:
            response = _opener.open(request, timeout=self.timeout_s)
            with self._response_lock:
                self._response = response
            validate_connected_peer(response)
            final_url = response.geturl() if hasattr(response, "geturl") else self.url
            validate_public_http_url(final_url)

            chunks: list[bytes] = []
            total = 0
            while True:
                if self._cancelled.is_set():
                    raise DownloadCancelledError("Bilddownload wurde abgebrochen.")
                chunk = response.read(min(64 * 1024, MAX_MEDIA_BYTES + 1 - total))
                if not chunk:
                    break
                chunks.append(chunk)
                total += len(chunk)
                if total > MAX_MEDIA_BYTES:
                    raise ValueError("Bilddatei ist zu groß.")
            if self._cancelled.is_set():
                raise DownloadCancelledError("Bilddownload wurde abgebrochen.")
            data = b"".join(chunks)
        except (OSError, ValueError, urllib.error.URLError) as exc:
            if self._cancelled.is_set() and not isinstance(exc, DownloadCancelledError):
                raise DownloadCancelledError("Bilddownload wurde abgebrochen.") from exc
            raise
        finally:
            with self._response_lock:
                self._response = None
            if response is not None:
                try:
                    response.close()
                except (OSError, ValueError):
                    pass

        if not data:
            raise ValueError("Leere Bilddatei erhalten.")
        suffix = detect_image_suffix(data)
        if suffix is None:
            raise ValueError("Die heruntergeladene Datei ist kein bekanntes Bildformat.")
        return data, suffix


MediaKind = Literal["images", "writing_samples", "documents"]


@dataclass(frozen=True)
class MediaImportResult:
    source: str
    target: Path
    copied: bool
    already_managed: bool = False


def safe_slug(value: str | None, *, fallback: str = "item", max_len: int = 80) -> str:
    """Dateisystemfreundlicher, stabiler Slug ohne externe Abhängigkeiten."""
    raw = str(value or "").strip() or fallback
    raw = unicodedata.normalize("NFKD", raw)
    raw = "".join(ch for ch in raw if not unicodedata.combining(ch))
    raw = raw.replace("ß", "ss")
    raw = re.sub(r"[^A-Za-z0-9._-]+", "_", raw).strip("._-")
    raw = re.sub(r"_+", "_", raw)
    return (raw[:max_len].strip("._-") or fallback).lower()


def media_root(data_dir: Path) -> Path:
    return Path(data_dir) / "media"


def pen_folder_name(pen_id: int | None, brand: str | None, model: str | None) -> str:
    label = "_".join(part for part in (safe_slug(brand, fallback="pen", max_len=35), safe_slug(model, fallback="model", max_len=45)) if part)
    prefix = f"{int(pen_id):04d}" if pen_id else "unassigned"
    return f"{prefix}_{label}" if label else prefix


def pen_media_dir(data_dir: Path, pen_id: int | None, brand: str | None, model: str | None) -> Path:
    return media_root(data_dir) / "pens" / pen_folder_name(pen_id, brand, model)


def pen_media_subdir(
    data_dir: Path,
    pen_id: int | None,
    brand: str | None,
    model: str | None,
    kind: MediaKind,
) -> Path:
    folder = pen_media_dir(data_dir, pen_id, brand, model) / kind
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def ensure_pen_media_tree(data_dir: Path, pen_id: int | None, brand: str | None, model: str | None) -> Path:
    base = pen_media_dir(data_dir, pen_id, brand, model)
    for kind in ("images", "writing_samples", "documents"):
        (base / kind).mkdir(parents=True, exist_ok=True)
    return base


def is_inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except Exception:
        return False


def is_managed_media_path(path: str | Path | None, data_dir: Path) -> bool:
    if not path:
        return False
    try:
        return is_inside(Path(path).expanduser(), media_root(data_dir))
    except Exception:
        return False


def _unique_path(folder: Path, stem: str, suffix: str) -> Path:
    suffix = suffix.lower() if suffix else ".jpg"
    if suffix and not suffix.startswith("."):
        suffix = "." + suffix
    candidate = folder / f"{stem}{suffix}"
    if not candidate.exists():
        return candidate
    for idx in range(2, 1000):
        candidate = folder / f"{stem}_{idx}{suffix}"
        if not candidate.exists():
            return candidate
    return folder / f"{stem}_{int(datetime.now().timestamp())}{suffix}"


def _suffix_from_source(source: str, *, default: str = ".jpg") -> str:
    parsed = urllib.parse.urlparse(source)
    suffix = Path(parsed.path or source).suffix.lower()
    return suffix if suffix in SUPPORTED_IMAGE_SUFFIXES else default


def download_image_bytes(url: str, *, timeout_s: int = DOWNLOAD_TIMEOUT_S) -> tuple[bytes, str]:
    """Load an image through the active, centrally SSRF-protected path."""
    return ImageDownloadOperation(url, timeout_s=timeout_s).download()


def _download_to(url: str, target: Path) -> Path:
    """Lädt nach ``target``; korrigiert die Endung auf das erkannte Format."""
    data, detected = download_image_bytes(url)
    if target.suffix.lower() != detected and not (
        detected == ".jpg" and target.suffix.lower() in (".jpg", ".jpeg")
    ):
        target = target.with_suffix(detected)
    target.write_bytes(data)
    return target


def import_media_asset(
    data_dir: Path,
    source: str | Path | None,
    *,
    pen_id: int | None,
    brand: str | None,
    model: str | None,
    kind: MediaKind,
    title: str | None = None,
    prefix: str | None = None,
) -> MediaImportResult | None:
    """Importiert lokale Bilder/URLs in die zentrale Medienstruktur.

    Bereits verwaltete Dateien unter ``<data_dir>/media`` werden nicht erneut
    kopiert. Nicht vorhandene lokale Pfade bleiben als externer Pfad erhalten,
    damit alte Daten nicht verloren gehen.
    """
    raw = str(source or "").strip()
    if not raw:
        return None

    data_dir = Path(data_dir)
    folder = pen_media_subdir(data_dir, pen_id, brand, model, kind)
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem_parts = [prefix or kind.rstrip("s"), now]
    if title:
        stem_parts.append(safe_slug(title, fallback="item", max_len=50))
    stem = "_".join(stem_parts)

    if raw.startswith(("http://", "https://")):
        target = _unique_path(folder, stem, _suffix_from_source(raw))
        target = _download_to(raw, target)
        return MediaImportResult(source=raw, target=target, copied=True)

    src = Path(raw).expanduser()
    if not src.exists() or not src.is_file():
        return MediaImportResult(source=raw, target=src, copied=False, already_managed=False)
    if is_managed_media_path(src, data_dir):
        return MediaImportResult(source=raw, target=src, copied=False, already_managed=True)

    suffix = src.suffix.lower()
    if suffix not in SUPPORTED_IMAGE_SUFFIXES:
        suffix = ".jpg"
    target = _unique_path(folder, stem, suffix)
    shutil.copy2(src, target)
    return MediaImportResult(source=raw, target=target, copied=True)


def import_pen_image(
    data_dir: Path,
    source: str | Path | None,
    *,
    pen_id: int | None,
    brand: str | None,
    model: str | None,
) -> str | None:
    result = import_media_asset(
        data_dir,
        source,
        pen_id=pen_id,
        brand=brand,
        model=model,
        kind="images",
        title="cover",
        prefix="pen_image",
    )
    return str(result.target) if result else None


def import_writing_sample_image(
    data_dir: Path,
    source: str | Path | None,
    *,
    pen_id: int | None,
    brand: str | None,
    model: str | None,
    title: str | None,
) -> str | None:
    result = import_media_asset(
        data_dir,
        source,
        pen_id=pen_id,
        brand=brand,
        model=model,
        kind="writing_samples",
        title=title,
        prefix="sample",
    )
    return str(result.target) if result else None
