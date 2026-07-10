"""Locale-aware Qt widgets and currency helpers.

Qt widgets normally inherit the operating-system locale. FountainPen Manager,
however, has an explicit app locale in its settings. This module keeps numeric
input and money affixes aligned with that app locale so Linux/Windows host
settings cannot silently change commas into points or vice versa.
"""
from __future__ import annotations

import re
from collections.abc import Iterable

from PySide6.QtGui import QValidator
from PySide6.QtWidgets import QComboBox, QDoubleSpinBox

from i18n.translator import (
    LocaleService,
    SUPPORTED_CURRENCIES,
    normalize_currency_code,
)


class LocalizedDoubleSpinBox(QDoubleSpinBox):
    """QDoubleSpinBox using the application's decimal separator.

    Both comma and point are accepted on input, while the displayed value always
    follows the active FountainPen Manager region. This avoids dangerous cases
    such as ``39,96`` being interpreted as ``3996``.
    """

    def textFromValue(self, value: float) -> str:  # noqa: N802 - Qt API
        return LocaleService.instance().format_number(
            value,
            self.decimals(),
            grouping=False,
        )

    def _numeric_text(self, text: str) -> str:
        cleaned = str(text)
        prefix = self.prefix()
        suffix = self.suffix()
        if prefix and cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
        if suffix and cleaned.endswith(suffix):
            cleaned = cleaned[:-len(suffix)]
        return cleaned.strip()

    def valueFromText(self, text: str) -> float:  # noqa: N802 - Qt API
        if self.specialValueText() and str(text).strip() == self.specialValueText():
            return self.minimum()
        value = LocaleService.instance().parse_number(self._numeric_text(text))
        return self.value() if value is None else value

    def validate(self, text: str, pos: int):  # noqa: N802 - Qt API
        if self.specialValueText() and str(text).strip() == self.specialValueText():
            return QValidator.State.Acceptable, text, pos
        numeric = self._numeric_text(text)
        if numeric in {"", "+", "-", ".", ",", "+.", "+,", "-.", "-,"}:
            return QValidator.State.Intermediate, text, pos
        if not re.fullmatch(r"[0-9.,'’`\s+\-]*", numeric):
            return QValidator.State.Invalid, text, pos
        value = LocaleService.instance().parse_number(numeric)
        if value is None:
            return QValidator.State.Intermediate, text, pos
        if self.minimum() <= value <= self.maximum():
            return QValidator.State.Acceptable, text, pos
        return QValidator.State.Intermediate, text, pos

    def fixup(self, text: str) -> str:
        value = LocaleService.instance().parse_number(self._numeric_text(text))
        if value is None:
            value = self.value()
        value = min(self.maximum(), max(self.minimum(), value))
        return self.textFromValue(value)

    def refresh_locale(self) -> None:
        """Repaint after a locale change without changing the stored value.

        Money fields remember their ISO code so a live region change can also
        move the code from prefix to suffix (or back) without reopening the
        dialog. Measurement fields simply redraw their decimal separator.
        """
        currency_code = getattr(self, "_fpm_currency_code", None)
        if currency_code:
            self.setPrefix("")
            self.setSuffix("")
            if LocaleService.instance().currency_position == "after":
                self.setSuffix(f" {currency_code}")
            else:
                self.setPrefix(f"{currency_code} ")
        if self.specialValueText() and self.value() == self.minimum():
            text = self.specialValueText()
        else:
            text = f"{self.prefix()}{self.textFromValue(self.value())}{self.suffix()}"
        self.lineEdit().setText(text)
        self.update()


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


def set_money_affix(spinbox: QDoubleSpinBox, currency: str | None = None) -> None:
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


def bind_currency_combo(combo: QComboBox, *spinboxes: QDoubleSpinBox) -> None:
    """Keep one or more money spinboxes synchronized with a currency combo."""
    def refresh(*_args) -> None:
        code = current_currency(combo)
        for spinbox in spinboxes:
            set_money_affix(spinbox, code)

    combo._fpm_refresh_currency = refresh
    combo.currentIndexChanged.connect(refresh)
    refresh()
