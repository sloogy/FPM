"""Locale-treue Dezimal- und Geldeingabe (v0.2.95).

Der gemeldete Fehler (`39,96 CHF` statt `CHF 39.96` bei deutscher OS-Locale)
entstand, weil ``QDoubleSpinBox`` Komma/Punkt von der Betriebssystem-Locale
übernimmt – unabhängig von der in der App gewählten Region. Diese Klassen
kappen diese Kopplung: Anzeige und Parsing laufen ausschließlich über den
``LocaleService`` der App.

- ``LocalizedDoubleSpinBox`` akzeptiert beim Tippen sowohl ``39,96`` als auch
  ``39.96`` und speichert immer denselben numerischen Wert.
- ``MoneySpinBox`` bindet zusätzlich einen Währungscode und zeigt ihn als
  Präfix oder Suffix passend zur Region (``CHF 39.96`` vs. ``39,96 EUR``).
"""
from __future__ import annotations

from PySide6.QtCore import QLocale
from PySide6.QtGui import QValidator
from PySide6.QtWidgets import QDoubleSpinBox

from i18n.translator import locale


def strip_spinbox_affixes(text: str, prefix: str = "", suffix: str = "") -> str:
    """Sichtbare SpinBox-Affixe entfernen, ohne Zahlzeichen zu verändern."""
    cleaned = str(text or "").strip()
    prefix = prefix or ""
    suffix = suffix or ""
    if prefix and cleaned.startswith(prefix):
        cleaned = cleaned[len(prefix):].lstrip()
    if suffix and cleaned.endswith(suffix):
        cleaned = cleaned[:-len(suffix)].rstrip()
    return cleaned


class LocalizedDoubleSpinBox(QDoubleSpinBox):
    """DoubleSpinBox, die die App-Region statt der OS-Locale verwendet."""

    def __init__(self, *args, decimals: int = 2, **kwargs):
        super().__init__(*args, **kwargs)
        # Qt soll nicht selbst nach OS-Locale gruppieren/parsen.
        self.setLocale(QLocale(QLocale.Language.C, QLocale.Country.AnyCountry))
        self.setGroupSeparatorShown(False)
        self.setDecimals(decimals)
        self.setMaximum(10_000_000.0)
        self.setKeyboardTracking(False)

    # --- Anzeige --------------------------------------------------------
    def textFromValue(self, value: float) -> str:
        # Ohne Tausendertrenner im editierbaren Feld (bewusste Vorgabe);
        # nur das regionale Dezimalzeichen.
        dec = locale()._decimal_sep or "."
        text = f"{value:.{self.decimals()}f}"
        return text.replace(".", dec) if dec != "." else text

    # --- Eingabe --------------------------------------------------------
    def _number_text(self, text: str) -> str:
        """Qt-Präfix/Suffix entfernen, bevor die App-Locale parst.

        ``QDoubleSpinBox.valueFromText()`` und ``validate()`` erhalten je nach
        Plattform den sichtbaren Text inklusive Affixen. Bei Feldern wie
        ``123.40 mm`` oder ``CHF 39.90`` führte das früher zu einem Parse-Fehler
        und beim Fokuswechsel zu einem Rücksprung auf 0.
        """
        return strip_spinbox_affixes(text, self.prefix(), self.suffix())

    def valueFromText(self, text: str) -> float:
        parsed = locale().parse_number(self._number_text(text))
        if parsed is None:
            # Ungültiger oder noch unvollständiger Text darf den zuletzt
            # bestätigten Wert nicht stillschweigend auf 0 zurücksetzen.
            return float(self.value())
        return float(parsed)

    def validate(self, text: str, pos: int):  # noqa: N802 (Qt-Signatur)
        stripped = self._number_text(text)
        if stripped in ("", "+", "-"):
            return (QValidator.State.Intermediate, text, pos)
        if locale().parse_number(stripped) is None:
            # Zwischenzustände beim Tippen (z. B. "39,") zulassen.
            if stripped and (stripped[-1] in ".,'" or stripped[-1].isdigit()):
                return (QValidator.State.Intermediate, text, pos)
            return (QValidator.State.Invalid, text, pos)
        return (QValidator.State.Acceptable, text, pos)

    def refresh_locale(self) -> None:
        """Anzeige und Währungsposition nach einem App-Regionwechsel erneuern."""
        currency_code = getattr(self, "_fpm_currency_code", None)
        if currency_code:
            self.setPrefix("")
            self.setSuffix("")
            if locale().currency_position == "after":
                self.setSuffix(f" {currency_code}")
            else:
                self.setPrefix(f"{currency_code} ")
        if self.specialValueText() and self.value() == self.minimum():
            text = self.specialValueText()
        else:
            text = f"{self.prefix()}{self.textFromValue(self.value())}{self.suffix()}"
        self.lineEdit().setText(text)
        self.update()


class MoneySpinBox(LocalizedDoubleSpinBox):
    """Dezimalfeld mit gebundenem Währungscode (Präfix/Suffix je Region)."""

    def __init__(self, *args, currency: str | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._currency: str = currency or locale()._currency
        self._apply_affix()

    def set_currency(self, code: str | None) -> None:
        """ISO-Code binden und Präfix/Suffix sofort neu zeichnen."""
        self._currency = (code or locale()._currency).strip()
        self._apply_affix()

    def currency(self) -> str:
        return self._currency

    def _apply_affix(self) -> None:
        # Position folgt der Region: CH/UK/US = Präfix, DE/AT/FR = Suffix.
        if locale()._currency_position == "after":
            self.setPrefix("")
            self.setSuffix(f" {self._currency}")
        else:
            self.setPrefix(f"{self._currency} ")
            self.setSuffix("")

    def refresh_locale(self) -> None:
        """Nach einem Regionwechsel Position und Dezimalzeichen neu anwenden."""
        self._apply_affix()
        # Wert neu setzen erzwingt textFromValue mit neuem Dezimalzeichen.
        self.setValue(self.value())
