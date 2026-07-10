"""Release-hardening checks for GitHub-ready source packages."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_release_version_metadata_is_current():
    src = (ROOT / "app_info.py").read_text(encoding="utf-8")
    assert 'APP_VERSION = "0.2.90"' in src
    assert 'APP_BUILD = "windows-path-release-fix"' in src


def test_i18n_runtime_does_not_translate_inside_longer_words():
    from i18n.translator import Translator
    from i18n.qt_i18n import translate_source_text

    tr = Translator.instance()
    old = tr.language
    try:
        for lang, expected in {
            "en": "Export completed:\n{}",
            "fr": "Export terminé :\n{}",
        }.items():
            tr.set_language(lang)
            translated = translate_source_text("Export abgeschlossen:\n{}", lang)
            assert translated == expected
            assert "abclosed" not in translated
            assert "abfermé" not in translated
    finally:
        tr.set_language(old)


def test_release_blocker_strings_use_explicit_translation_keys():
    srcs = {
        "ink": (ROOT / "ui" / "ink_widget.py").read_text(encoding="utf-8"),
        "settings": (ROOT / "ui" / "settings_widget.py").read_text(encoding="utf-8"),
        "wishlist": (ROOT / "ui" / "wishlist_widget.py").read_text(encoding="utf-8"),
        "pen": (ROOT / "ui" / "pen_widget.py").read_text(encoding="utf-8"),
        "rotation": (ROOT / "ui" / "rotation_widget.py").read_text(encoding="utf-8"),
    }
    forbidden = [
        '"Kein Limit"', '"🔴 Überfällig!"',
        "f'Export abgeschlossen", "f'{count} aktive InkLoad(s) geschlossen.'",
        '"Typ"', '"Erwarteter Preis"', '"Tatsächlicher Preis"', '"Warum will ich das?"',
        "'📦 Archivieren'", "'✏  Bearbeiten'", "'🖋  Tinte einfüllen'",
    ]
    combined = "\n".join(srcs.values())
    for needle in forbidden:
        assert needle not in combined
