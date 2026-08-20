"""Locale-aware Qt widgets and currency helpers.

Qt widgets normally inherit the operating-system locale. FountainPen Manager,
however, has an explicit app locale in its settings. This module keeps numeric
input and money affixes aligned with that app locale so Linux/Windows host
settings cannot silently change commas into points or vice versa.
"""
from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtWidgets import QComboBox

from i18n.translator import (
    LocaleService,
    SUPPORTED_CURRENCIES,
    normalize_currency_code,
)
from ui.localized_inputs import LocalizedDoubleSpinBox


def populate_currency_combo(
    combo: QComboBox,
    selected: str | None = None,
    currencies: Iterable[str] = SUPPORTED_CURRENCIES,
) -> None:
    """Fill a combo with stable ISO codes; currency codes are never translated."""
    wanted = normalize_currency_code(selected, LocaleService.instance().currency)
    combo.blockSignals(True)
    combo.clear()
    for code in currencies:
        normalized = str(code).strip().upper()
        combo.addItem(normalized, normalized)
    index = combo.findData(wanted)
    combo.setCurrentIndex(index if index >= 0 else 0)
    combo.blockSignals(False)


def current_currency(combo: QComboBox, fallback: str | None = None) -> str:
    value = combo.currentData() or combo.currentText()
    return normalize_currency_code(
        value,
        fallback or LocaleService.instance().currency,
    )


def set_combo_currency(combo: QComboBox, currency: str | None) -> None:
    code = normalize_currency_code(currency, LocaleService.instance().currency)
    index = combo.findData(code)
    if index < 0:
        index = combo.findText(code)
    if index >= 0:
        combo.setCurrentIndex(index)
    refresh = getattr(combo, "_fpm_refresh_currency", None)
    if callable(refresh):
        refresh()


def set_money_affix(spinbox: LocalizedDoubleSpinBox, currency: str | None = None) -> None:
    """Apply the currency code as prefix/suffix according to app region."""
    service = LocaleService.instance()
    code = normalize_currency_code(currency, service.currency)
    spinbox._fpm_currency_code = code
    spinbox.setPrefix("")
    spinbox.setSuffix("")
    if service.currency_position == "after":
        spinbox.setSuffix(f" {code}")
    else:
        spinbox.setPrefix(f"{code} ")
    if hasattr(spinbox, "refresh_locale"):
        spinbox.refresh_locale()


def bind_currency_combo(combo: QComboBox, *spinboxes: LocalizedDoubleSpinBox) -> None:
    """Keep one or more money spinboxes synchronized with a currency combo."""
    def refresh(*_args) -> None:
        code = current_currency(combo)
        for spinbox in spinboxes:
            set_money_affix(spinbox, code)

    combo._fpm_refresh_currency = refresh
    combo.currentIndexChanged.connect(refresh)
    refresh()
