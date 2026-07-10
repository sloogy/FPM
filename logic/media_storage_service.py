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
import urllib.parse
import urllib.request
import unicodedata
from typing import Literal

SUPPORTED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}
MAX_MEDIA_BYTES = 15 * 1024 * 1024

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


def _download_to(url: str, target: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "FountainPenManager/media-import"})
    with urllib.request.urlopen(request, timeout=15) as response:
        data = response.read(MAX_MEDIA_BYTES + 1)
    if not data:
        raise ValueError("Leere Bilddatei erhalten.")
    if len(data) > MAX_MEDIA_BYTES:
        raise ValueError("Bilddatei ist zu groß.")
    target.write_bytes(data)


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
        _download_to(raw, target)
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
