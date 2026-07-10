"""v0.2.81: Guard – die In-App-Hilfe deckt die Kern-Workflows ab.

Hintergrund: Nach dem Featureschub 0.2.79/0.2.80 fehlten in der Hilfe genau
die Kapitel, die ein neuer Nutzer zuerst braucht (Vorschlags-Workflow,
Reroll, Zufallsregler, Hersteller-Recherche, Overlay-Datei). Dieser Test
verhindert, dass künftige Features wieder ohne Hilfe-Kapitel landen.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _src(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _lang(lang: str) -> dict:
    return json.loads((ROOT / "i18n" / f"{lang}.json").read_text(encoding="utf-8"))


def _get(d: dict, dotted: str):
    node = d
    for part in dotted.split("."):
        assert isinstance(node, dict) and part in node, f"{dotted} fehlt"
        node = node[part]
    assert isinstance(node, str) and node.strip(), f"{dotted} leer"
    return node


def test_help_widget_registers_rotation_and_research_tabs():
    src = _src("ui/help_widget.py")
    assert "_add_rotation_tab" in src and "_add_research_tab" in src
    # Reihenfolge: Rotation direkt nach Start (Kern-Workflow früh), Recherche vor Glossar
    order = [src.index(x) for x in (
        "self._add_start_tab(tabs)", "self._add_rotation_tab(tabs)",
        "self._add_rules_tab(tabs)", "self._add_research_tab(tabs)",
        "self._add_glossary_tab(tabs)",
    )]
    assert order == sorted(order)
    # Dashboard-Karte im Start-Tab
    assert "help.dashboard_title" in src and "help.dashboard_body" in src


def test_help_keys_exist_and_are_substantial_in_all_languages():
    keys = [
        "help.dashboard_title", "help.dashboard_body",
        "help.rotation.tab", "help.rotation.workflow_body", "help.rotation.score_body",
        "help.rotation.reroll_body", "help.rotation.random_body", "help.rotation.pins_body",
        "help.research.tab", "help.research.lookup_body", "help.research.sources_body",
        "help.research.overlay_body",
        "rotation.generate_tooltip",
    ]
    for lang in ("de", "en", "fr"):
        data = _lang(lang)
        for key in keys:
            text = _get(data, key)
            if key.endswith("_body"):
                assert len(text) > 120, f"{lang}:{key} zu dünn für eine Hilfekarte"


def test_help_rotation_chapter_covers_the_new_mechanics():
    de = _lang("de")["help"]["rotation"]
    blob = " ".join(de.values())
    for needle in ("💍", "⭐", "🔁", "Zufall", "Score"):
        assert needle in blob, f"Rotation-Hilfe erwähnt {needle!r} nicht"
    # Zufalls-Kapitel nennt die Sicherheitsgrenze
    assert "beschädigen" in de["random_body"] or "blockierende" in de["random_body"]


def test_help_research_chapter_documents_overlay_and_sources():
    for lang in ("de", "en", "fr"):
        research = _lang(lang)["help"]["research"]
        assert "manufacturer_domains.json" in research["overlay_body"]
        assert "manufacturer:" in research["sources_body"]
        # JSON-Beispiel mit Listen-Variante vorhanden
        assert "pilotpen.eu" in research["overlay_body"]


def test_quickstart_now_ends_with_suggestions_step():
    for lang in ("de", "en", "fr"):
        body = _lang(lang)["help"]["quickstart_body"]
        assert "5." in body
        assert "💡" in body


def test_glossary_extended_to_twelve_terms():
    src = _src("ui/help_widget.py")
    for key in (
        "glossary_edc_desc", "glossary_vac_desc", "glossary_fixed_desc",
        "glossary_must_desc", "glossary_hard_soft_desc", "glossary_reroll_desc",
    ):
        assert key in src
    for lang in ("de", "en", "fr"):
        hw = _lang(lang)["ui"]["help_widget"]
        for key in (
            "glossary_edc_desc", "glossary_vac_desc", "glossary_fixed_term",
            "glossary_fixed_desc", "glossary_must_term", "glossary_must_desc",
            "glossary_hard_soft_term", "glossary_hard_soft_desc",
            "glossary_reroll_desc",
        ):
            assert key in hw and hw[key].strip(), f"{lang}: {key}"


def test_generate_button_has_reroll_tooltip():
    src = _src("ui/rotation_widget.py")
    assert '"rotation.generate_tooltip"' in src
    assert "b.setToolTip(t(tip_key))" in src


def test_help_body_texts_survive_t_formatting():
    """Hilfetexte enthalten { } (JSON-Beispiel) – t() ohne kwargs darf sie nie formatieren.

    Guard: help-Karten werden im Widget ohne Parameter aufgerufen.
    """
    src = _src("ui/help_widget.py")
    assert "t('help.research.overlay_body')" in src  # kein kwargs-Aufruf
    assert "t('help.research.overlay_body'," not in src
