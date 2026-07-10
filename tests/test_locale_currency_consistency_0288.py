"""v0.2.88: currency display/input must follow the app locale, not the OS."""
from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QComboBox

from i18n.translator import (
    LocaleService,
    REGION_PRESETS,
    SUPPORTED_CURRENCIES,
    normalize_currency_code,
    normalize_number_separators,
)
from ui.locale_widgets import (
    LocalizedDoubleSpinBox,
    bind_currency_combo,
    current_currency,
    populate_currency_combo,
    set_combo_currency,
    set_money_affix,
)

ROOT = Path(__file__).resolve().parents[1]


def _service(*, decimal: str, thousands: str, currency: str, position: str) -> LocaleService:
    service = LocaleService.__new__(LocaleService)
    service._decimal_sep = decimal
    service._thousands_sep = thousands
    service._currency = currency
    service._currency_position = position
    service._date_format = "DD.MM.YYYY"
    service._exchange_rates = {"CHF": 1.0, "EUR": 0.95, "USD": 1.08, "GBP": 0.81}
    return service


def _set_service(service: LocaleService):
    old = LocaleService._instance
    LocaleService._instance = service
    return old


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_parser_accepts_comma_and_point_without_factor_error():
    parse = LocaleService.parse_localized_number
    assert parse("39,96", ".", "'") == 39.96
    assert parse("39.96", ",", ".") == 39.96
    assert parse("CHF 39,96", ".", "'") == 39.96
    assert parse("1.234,56 EUR", ",", ".") == 1234.56
    assert parse("USD 1,234.56", ".", ",") == 1234.56
    assert parse("1'234.56", ".", "'") == 1234.56
    assert parse("1 234,56", ",", " ") == 1234.56
    assert parse("1,234", ".", "'") == 1234.0
    assert parse(",5", ",", ".") == 0.5
    assert parse("50 ml", ".", "'") == 50.0
    assert parse("1/2", ".", "'") is None
    assert parse("1e3", ".", "'") is None
    assert parse("12,34,56", ".", "'") is None
    assert parse("12.34,56", ",", ".") is None
    assert parse("1.234.567,89", ",", ".") == 1234567.89
    assert parse("not a number", ".", "'") is None


def test_currency_normalization_is_language_independent():
    assert normalize_currency_code("chf", "EUR") == "CHF"
    assert normalize_currency_code("Fr.", "EUR") == "CHF"
    assert normalize_currency_code("€", "CHF") == "EUR"
    assert normalize_currency_code("US$", "CHF") == "USD"
    assert normalize_currency_code("£", "CHF") == "GBP"
    assert normalize_currency_code("invalid", "EUR") == "EUR"


def test_ch_and_de_money_formatting_are_consistent():
    ch = _service(decimal=".", thousands="'", currency="CHF", position="before")
    assert ch.format_number(1234.56) == "1'234.56"
    assert ch.format_money(39.96) == "CHF 39.96"
    assert ch.format_money(39.96, "EUR") == "EUR 39.96"

    de = _service(decimal=",", thousands=".", currency="EUR", position="after")
    assert de.format_number(1234.56) == "1.234,56"
    assert de.format_money(39.96) == "39,96 EUR"
    assert de.format_money(39.96, "CHF") == "39,96 CHF"


def test_missing_currency_is_treated_as_default_not_as_chf():
    de = _service(decimal=",", thousands=".", currency="EUR", position="after")
    assert de.convert_to_default(100.0, None) == 100.0
    assert round(de.convert_to_default(100.0, "CHF"), 2) == 95.0


def test_localized_spinbox_uses_app_locale_and_accepts_both_separators():
    _app()
    old = _set_service(_service(decimal=".", thousands="'", currency="CHF", position="before"))
    try:
        spin = LocalizedDoubleSpinBox()
        spin.setRange(0, 100000)
        spin.setDecimals(2)
        set_money_affix(spin, "CHF")
        spin.setValue(39.96)
        assert spin.text() == "CHF 39.96"
        assert spin.valueFromText("CHF 39,96") == 39.96
        assert spin.valueFromText("CHF 39.96") == 39.96
    finally:
        LocaleService._instance = old


def test_special_zero_text_is_not_overwritten_by_currency_affix():
    _app()
    old = _set_service(_service(decimal=".", thousands="'", currency="CHF", position="before"))
    try:
        spin = LocalizedDoubleSpinBox()
        spin.setRange(0, 1000)
        spin.setDecimals(2)
        spin.setSpecialValueText("No limit")
        spin.setValue(0)
        set_money_affix(spin, "CHF")
        assert spin.text() == "No limit"
        assert spin.valueFromText("No limit") == 0
    finally:
        LocaleService._instance = old


def test_currency_combo_updates_money_affix_and_preserves_iso_codes():
    _app()
    old = _set_service(_service(decimal=",", thousands=".", currency="EUR", position="after"))
    try:
        combo = QComboBox()
        spin = LocalizedDoubleSpinBox()
        spin.setDecimals(2)
        populate_currency_combo(combo)
        bind_currency_combo(combo, spin)
        assert [combo.itemData(i) for i in range(combo.count())] == list(SUPPORTED_CURRENCIES)
        assert current_currency(combo) == "EUR"
        assert spin.suffix() == " EUR"
        set_combo_currency(combo, "CHF")
        assert current_currency(combo) == "CHF"
        assert spin.suffix() == " CHF"
        assert spin.prefix() == ""
    finally:
        LocaleService._instance = old


def test_iso_currency_translation_keys_never_change_codes():
    expected_by_prefix = {"chf_": "CHF", "eur_": "EUR", "usd_": "USD", "gbp_": "GBP"}
    for language in ("de", "en", "fr"):
        data = json.loads((ROOT / "i18n" / f"{language}.json").read_text(encoding="utf-8"))
        found = 0
        stack = [data]
        while stack:
            node = stack.pop()
            if not isinstance(node, dict):
                continue
            for key, value in node.items():
                if isinstance(value, dict):
                    stack.append(value)
                    continue
                for prefix, expected in expected_by_prefix.items():
                    if key.startswith(prefix):
                        assert value == expected, (language, key, value)
                        found += 1
        assert found >= 16


def test_all_ui_decimal_spinboxes_use_app_locale_wrapper():
    direct_imports = []
    for path in (ROOT / "ui").glob("*.py"):
        if path.name == "locale_widgets.py":
            continue
        src = path.read_text(encoding="utf-8")
        if "from PySide6.QtWidgets" in src and "QDoubleSpinBox" in src:
            # Stylesheet strings are harmless; only direct widget imports are forbidden.
            import_lines = "\n".join(line for line in src.splitlines()[:80])
            if "QDoubleSpinBox" in import_lines and "LocalizedDoubleSpinBox as QDoubleSpinBox" not in import_lines:
                direct_imports.append(path.name)
    assert not direct_imports, direct_imports


def test_currency_widgets_do_not_use_translated_iso_labels_or_raw_suffixes():
    for name in ("pen_widget.py", "ink_widget.py", "paper_widget.py", "wishlist_widget.py", "expenses_widget.py"):
        src = (ROOT / "ui" / name).read_text(encoding="utf-8")
        assert ".addItems([t('ui." not in src or "chf_" not in src
        assert "setSuffix(f' {default_cur}')" not in src
        assert 'setSuffix(f" {default_cur}")' not in src


def test_exchange_rate_error_key_exists_in_all_languages():
    for language in ("de", "en", "fr"):
        data = json.loads((ROOT / "i18n" / f"{language}.json").read_text(encoding="utf-8"))
        assert "{currency}" in data["settings"]["invalid_exchange_rate"]


def test_number_separator_settings_are_sanitized_and_unambiguous():
    assert normalize_number_separators(",", ".") == (",", ".")
    assert normalize_number_separators(",", " ") == (",", " ")
    assert normalize_number_separators(".", "") == (".", "")
    assert normalize_number_separators(",", ",") == (",", "")
    assert normalize_number_separators("invalid", "invalid") == (".", "'")


def test_settings_support_space_grouping_and_separate_radio_groups():
    src = (ROOT / "ui" / "settings_widget.py").read_text(encoding="utf-8")
    assert "self.thou_space_rb" in src
    assert "' ': self.thou_space_rb" in src
    assert "self.decimal_group = QButtonGroup" in src
    assert "self.thousands_group = QButtonGroup" in src
    assert "settings.separators_must_differ" in src


def test_separator_translation_keys_exist_in_all_languages():
    for language in ("de", "en", "fr"):
        data = json.loads((ROOT / "i18n" / f"{language}.json").read_text(encoding="utf-8"))
        assert "1 234" in data["settings"]["thousands_space"]
        assert data["settings"]["separators_must_differ"].strip()


def test_all_region_presets_have_deterministic_money_format():
    expected = {
        "CH": "CHF 1'234.56",
        "DE": "1.234,56 EUR",
        "AT": "1.234,56 EUR",
        "FR": "1 234,56 EUR",
        "GB": "GBP 1,234.56",
        "US": "USD 1,234.56",
        "EU": "1.234,56 EUR",
    }
    for code, preset in REGION_PRESETS.items():
        service = _service(
            decimal=preset["decimal_sep"],
            thousands=preset["thousands_sep"],
            currency=preset["currency"],
            position=preset["currency_position"],
        )
        assert service.format_money(1234.56) == expected[code]


def test_live_locale_change_moves_currency_affix_without_reopening_widget():
    _app()
    old = _set_service(_service(decimal=".", thousands="'", currency="CHF", position="before"))
    try:
        spin = LocalizedDoubleSpinBox()
        spin.setDecimals(2)
        spin.setValue(39.96)
        set_money_affix(spin, "CHF")
        assert spin.text() == "CHF 39.96"
        LocaleService._instance = _service(decimal=",", thousands=".", currency="EUR", position="after")
        spin.refresh_locale()
        assert spin.text() == "39,96 CHF"
        assert spin.prefix() == ""
        assert spin.suffix() == " CHF"
    finally:
        LocaleService._instance = old
