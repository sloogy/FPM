"""v0.2.94: Locale-/Währungs-Härtung – der gemeldete Faktor-100-Bug.

Kern des gemeldeten Fehlers: ``39,96`` wurde bei Punkt-Dezimalregion als
``3996`` geparst, und ``QDoubleSpinBox`` übernahm die OS-Locale statt der
App-Region. Diese Tests prüfen den regionunabhängigen Parser real und die
Verdrahtung der zentralen Eingabe-Komponente statisch (Qt nicht startbar).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from i18n.translator import LocaleService  # noqa: E402


def _ls(dec: str, thou: str) -> LocaleService:
    ls = LocaleService.__new__(LocaleService)
    ls._decimal_sep = dec
    ls._thousands_sep = thou
    ls._currency = "CHF"
    ls._currency_position = "before"
    return ls


def _src(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


# ── Der gemeldete Bug: 39,96 darf nie 3996 werden ───────────────────
def test_reported_bug_comma_input_in_dot_region():
    ls = _ls(".", "'")
    assert ls.parse_number("39,96") == 39.96      # war 3996.0
    assert ls.parse_number("39.96") == 39.96


def test_both_separators_yield_same_value_all_regions():
    for dec, thou in ((".", "'"), (",", "."), (",", " "), (".", ",")):
        ls = _ls(dec, thou)
        assert ls.parse_number("39,96") == 39.96, (dec, thou)
        assert ls.parse_number("39.96") == 39.96, (dec, thou)
        assert ls.parse_number("1234") == 1234.0, (dec, thou)


def test_grouped_values_are_parsed():
    ls = _ls(".", "'")
    assert ls.parse_number("1'234.56") == 1234.56      # Schweizer Apostroph
    assert ls.parse_number("1.234,56") == 1234.56      # deutsch
    assert ls.parse_number("1 234,56") == 1234.56      # französisch
    assert ls.parse_number("1,234.56") == 1234.56      # englisch


def test_malformed_grouping_is_rejected():
    ls = _ls(".", "'")
    assert ls.parse_number("12,34,56") is None
    assert ls.parse_number("1,23,456") is None


def test_currency_symbols_and_whitespace_are_stripped():
    ls = _ls(".", "'")
    assert ls.parse_number("CHF 39.96") == 39.96
    assert ls.parse_number("39,96 EUR") == 39.96
    assert ls.parse_number("\u202f1\u00a0234,56") == 1234.56


def test_sign_and_edge_cases():
    ls = _ls(".", "'")
    assert ls.parse_number("-5,5") == -5.5
    assert ls.parse_number("+3.0") == 3.0
    assert ls.parse_number("") is None
    assert ls.parse_number("   ") is None
    assert ls.parse_number("abc") is None
    assert ls.parse_number(None) is None


# ── Zentrale Eingabe-Komponente ──────────────────────────────────────
def test_localized_spinbox_module_exists():
    src = _src("ui/localized_inputs.py")
    assert "class LocalizedDoubleSpinBox" in src
    assert "class MoneySpinBox" in src
    # kappt die OS-Locale-Kopplung
    assert "QLocale.Language.C" in src
    assert "setGroupSeparatorShown(False)" in src
    # nutzt den App-Parser statt float()
    assert "locale().parse_number" in src


def test_all_decimal_widgets_use_localized_spinbox():
    """Kein rohes QDoubleSpinBox() mehr in den Datenerfassungs-Widgets."""
    # v0.3.03: pen_widget enthält nach dem Split keine Eingabefelder mehr –
    # das Roh-Spinbox-Verbot gilt weiter, die Localized-Pflicht nur für
    # Dateien mit Dezimal-Eingaben (Dialoge/übrige Widgets).
    no_raw = [
        "pen_widget", "pen_dialogs", "ink_widget", "paper_widget",
        "expenses_widget", "wishlist_widget", "enthusiast_lab_widget",
        "writing_samples_widget",
    ]
    must_localized = [w for w in no_raw if w != "pen_widget"]
    for w in no_raw:
        assert "QDoubleSpinBox()" not in _src(f"ui/{w}.py"), w
    for w in must_localized:
        assert "LocalizedDoubleSpinBox" in _src(f"ui/{w}.py"), w


def test_money_spinbox_binds_currency_prefix_or_suffix():
    src = _src("ui/localized_inputs.py")
    assert "def set_currency" in src
    assert "def refresh_locale" in src
    assert '_currency_position == "after"' in src


# ── CSV-Import nutzt denselben Parser ────────────────────────────────
def test_csv_import_uses_locale_parser_not_naive_replace():
    for rel in ("ui/pen_widget.py", "ui/ink_widget.py"):
        src = _src(rel)
        block = src.split("def to_float")[1].split("def ")[0]
        assert "parse_number" in block, rel
        assert ".replace(',', '.')" not in block and '.replace(",", ".")' not in block, rel


def test_exchange_rates_use_locale_parser_and_reject_nonpositive():
    src = _src("ui/settings_widget.py")
    block = src.split("for row, fx_cur in enumerate(self._fx_currencies)")[1][:400]
    assert "parse_localized_number" in block
    assert "<= 0" in block


# ── Währungscodes bleiben stabile ISO-Codes ──────────────────────────
def test_currency_codes_are_iso_not_translated():
    for rel in ("ui/expenses_widget.py", "ui/pen_dialogs.py", "ui/settings_widget.py"):
        src = _src(rel)
        assert '"CHF", "EUR", "USD", "GBP"' in src or "'CHF', 'EUR', 'USD', 'GBP'" in src, rel
