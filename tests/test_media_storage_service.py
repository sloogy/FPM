from pathlib import Path

from logic.media_storage_service import (
    ensure_pen_media_tree,
    import_pen_image,
    import_writing_sample_image,
    is_managed_media_path,
    pen_media_dir,
    safe_slug,
)


def test_safe_slug_handles_umlauts_spaces_and_symbols():
    assert safe_slug("Faber-Castell Essentio Grün") == "faber-castell_essentio_grun"
    assert safe_slug("", fallback="pen") == "pen"


def test_pen_image_import_lands_in_central_pen_folder(tmp_path):
    src = tmp_path / "input image.JPG"
    src.write_bytes(b"fake-image")

    target = import_pen_image(tmp_path, src, pen_id=12, brand="Faber-Castell", model="Essentio")

    assert target is not None
    path = Path(target)
    assert path.exists()
    assert path.read_bytes() == b"fake-image"
    assert path.parent.name == "images"
    assert path.parent.parent.name.startswith("0012_faber-castell_essentio")
    assert is_managed_media_path(path, tmp_path)


def test_existing_managed_media_is_not_copied_again(tmp_path):
    base = ensure_pen_media_tree(tmp_path, 1, "Pilot", "Custom 74")
    managed = base / "images" / "already.jpg"
    managed.write_bytes(b"x")

    target = import_pen_image(tmp_path, managed, pen_id=1, brand="Pilot", model="Custom 74")

    assert target == str(managed)
    assert len(list((base / "images").iterdir())) == 1


def test_writing_sample_image_lands_below_same_pen(tmp_path):
    src = tmp_path / "sample.png"
    src.write_bytes(b"sample")

    target = import_writing_sample_image(
        tmp_path,
        src,
        pen_id=7,
        brand="Pelikan",
        model="M800",
        title="Oxford Test",
    )

    path = Path(target)
    assert path.exists()
    assert path.parent.name == "writing_samples"
    assert path.parent.parent == pen_media_dir(tmp_path, 7, "Pelikan", "M800")
    assert "oxford_test" in path.stem
