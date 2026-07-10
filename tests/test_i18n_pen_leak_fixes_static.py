"""v0.2.73: Guards gegen erneute hartcodierte deutsche UI-Strings im Füllerbereich.

Diese Strings rutschten am Wiring-Audit vorbei, weil sie an Variablen zugewiesen
bzw. in f-Strings eingebettet waren. Der Test hält sie dauerhaft fern.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_pen_widget_has_no_hardcoded_german_status():
    src = _read("ui/pen_widget.py")
    # Früher hartcodiert – dürfen nicht zurückkehren.
    assert "'🔧 Service'" not in src
    assert "'🧼 Austrocknung'" not in src
    assert "'🔒 Gesperrt'" not in src
    assert "Rotation gesperrt{" not in src
    assert "f' bis {" not in src
    assert "<b>App-Logik:</b>" not in src
    # Stattdessen der übersetzte Mechanismus.
    assert "_status_label(_status)" in src
    assert "ui.pen_widget.until_suffix" in src
    assert "ui.pen_widget.rotation_blocked" in src
    assert "ui.pen_widget.service_help_footer" in src


def test_new_pen_keys_present_in_all_languages():
    import json
    keys = [
        "ui.pen_widget.until_suffix",
        "ui.pen_widget.rotation_blocked",
        "ui.pen_widget.service_help_footer",
    ]
    for lg in ("de", "en", "fr"):
        d = json.loads((ROOT / "i18n" / f"{lg}.json").read_text(encoding="utf-8"))
        for dotted in keys:
            cur = d
            for part in dotted.split("."):
                assert isinstance(cur, dict) and part in cur, f"{lg}:{dotted}"
                cur = cur[part]
            assert isinstance(cur, str) and cur.strip(), f"{lg}:{dotted}"
    # until_suffix muss den {date}-Platzhalter enthalten.
    for lg in ("de", "en", "fr"):
        d = json.loads((ROOT / "i18n" / f"{lg}.json").read_text(encoding="utf-8"))
        assert "{date}" in d["ui"]["pen_widget"]["until_suffix"], lg


def test_generate_manifest_example_uses_current_version():
    src = _read("updater/generate_manifest.py")
    assert "2.2.9" not in src  # Fremdversion aus BudgetManager darf nicht auftauchen
    assert "--version 0.2.87" in src


def test_rotation_widget_uses_hard_rule_suffix_key():
    """v0.2.87: Der Suffix ' (harte Regel)' existierte als i18n-Key, war aber
    nicht verdrahtet – die Codestelle nutzte ein deutsches Literal (EN/FR-Leak)."""
    src = _read("ui/rotation_widget.py")
    assert '" (harte Regel)"' not in src
    assert "rotation.warning_hard_rule_suffix" in src
