"""Regressionen für den beim Fokuswechsel verlorenen Füller-Formularwert."""
from __future__ import annotations

from i18n.translator import LocaleService
from ui.localized_inputs import strip_spinbox_affixes


def test_unit_suffix_is_removed_before_number_parsing():
    service = LocaleService.instance()
    for visible, suffix, expected in (
        ("123.40 mm", " mm", 123.4),
        ("28,75 g", " g", 28.75),
        ("1.20 ml", " ml", 1.2),
    ):
        cleaned = strip_spinbox_affixes(visible, suffix=suffix)
        assert service.parse_number(cleaned) == expected


def test_money_prefix_and_suffix_are_removed_before_number_parsing():
    service = LocaleService.instance()
    assert service.parse_number(strip_spinbox_affixes("CHF 39.96", prefix="CHF ")) == 39.96
    assert service.parse_number(strip_spinbox_affixes("19,95 EUR", suffix=" EUR")) == 19.95


def test_affix_stripping_does_not_damage_sign_or_decimal_separator():
    assert strip_spinbox_affixes("CHF -12,50", prefix="CHF ") == "-12,50"
    assert strip_spinbox_affixes("+7.25 mm", suffix=" mm") == "+7.25"


def test_runtime_source_preserves_previous_value_on_invalid_text():
    source = open("ui/localized_inputs.py", encoding="utf-8").read()
    assert "return float(self.value())" in source
    assert "locale().parse_number(self._number_text(text))" in source
