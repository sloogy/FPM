"""
Übersetzungssystem – lädt JSON-Dateien, stellt t() und LocaleService bereit.

v0.2.17 – Locale-System:
- LocaleService liest regional settings aus AppSettings (DB).
- Fallback auf Locale-Defaults der aktiven Sprach-JSON.
- format_money() und format_number() für einheitliche Darstellung.
- Regionsvoreinstellungen: CH, DE, AT, FR, GB, US.
"""
import json
import math
import re
from pathlib import Path
from typing import Any, Optional


# ── Regionsvoreinstellungen ───────────────────────────────────────────────────

REGION_PRESETS: dict[str, dict] = {
    "CH": {"label": "🇨🇭  Schweiz (CH)",   "currency": "CHF", "decimal_sep": ".",  "thousands_sep": "'",  "currency_position": "before", "date_format": "DD.MM.YYYY"},
    "DE": {"label": "🇩🇪  Deutschland (DE)", "currency": "EUR", "decimal_sep": ",",  "thousands_sep": ".",  "currency_position": "after",  "date_format": "DD.MM.YYYY"},
    "AT": {"label": "🇦🇹  Österreich (AT)",  "currency": "EUR", "decimal_sep": ",",  "thousands_sep": ".",  "currency_position": "after",  "date_format": "DD.MM.YYYY"},
    "FR": {"label": "🇫🇷  Frankreich (FR)",  "currency": "EUR", "decimal_sep": ",",  "thousands_sep": " ",  "currency_position": "after",  "date_format": "DD/MM/YYYY"},
    "GB": {"label": "🇬🇧  Grossbritannien (GB)", "currency": "GBP", "decimal_sep": ".", "thousands_sep": ",", "currency_position": "before", "date_format": "DD/MM/YYYY"},
    "US": {"label": "🇺🇸  USA (US)",         "currency": "USD", "decimal_sep": ".",  "thousands_sep": ",",  "currency_position": "before", "date_format": "MM/DD/YYYY"},
    "EU": {"label": "🇪🇺  Europa (EU/EUR)",   "currency": "EUR", "decimal_sep": ",",  "thousands_sep": ".",  "currency_position": "after",  "date_format": "DD.MM.YYYY"},
}

DATE_FORMAT_OPTIONS: dict[str, str] = {
    "DD.MM.YYYY": "31.12.2026",
    "DD/MM/YYYY": "31/12/2026",
    "MM/DD/YYYY": "12/31/2026",
    "YYYY-MM-DD": "2026-12-31",
}

# Standard-Wechselkurse (1 CHF = x Fremdwährung)
SUPPORTED_CURRENCIES: tuple[str, ...] = ("CHF", "EUR", "USD", "GBP")
CURRENCY_ALIASES: dict[str, str] = {
    "CHF": "CHF", "SFR": "CHF", "FR": "CHF", "FR.": "CHF",
    "EUR": "EUR", "€": "EUR",
    "USD": "USD", "US$": "USD", "$": "USD",
    "GBP": "GBP", "£": "GBP",
}


def normalize_currency_code(value: object, fallback: str = "CHF") -> str:
    """Return a supported ISO currency code.

    UI language must never translate an ISO code. Common symbols/legacy labels
    are accepted for CSV import; unknown values fall back deterministically.
    """
    raw = str(value or "").strip().upper()
    normalized = CURRENCY_ALIASES.get(raw, raw)
    if normalized in SUPPORTED_CURRENCIES:
        return normalized
    fallback_raw = str(fallback or "CHF").strip().upper()
    fallback_normalized = CURRENCY_ALIASES.get(fallback_raw, fallback_raw)
    return fallback_normalized if fallback_normalized in SUPPORTED_CURRENCIES else "CHF"


def normalize_number_separators(
    decimal_sep: object,
    thousands_sep: object,
) -> tuple[str, str]:
    """Validate persisted number separators and remove ambiguous combinations.

    The decimal separator is limited to comma or point. Supported grouping
    separators are apostrophe, comma, point, normal space and no separator.
    A separator can never be both decimal and grouping separator; corrupted or
    legacy settings therefore fall back safely instead of producing values such
    as ``1,234,56``.
    """
    decimal = str(decimal_sep) if decimal_sep is not None else "."
    thousands = str(thousands_sep) if thousands_sep is not None else "'"
    if decimal not in {".", ","}:
        decimal = "."
    if thousands not in {"'", ".", ",", " ", ""}:
        thousands = "'"
    if thousands == decimal:
        thousands = ""
    return decimal, thousands


DEFAULT_EXCHANGE_RATES: dict[str, float] = {
    "CHF": 1.0,
    "EUR": 0.95,
    "USD": 1.08,
    "GBP": 0.81,
}


# ── Translator ────────────────────────────────────────────────────────────────

class Translator:
    _instance: "Translator | None" = None

    def __init__(self):
        self._data: dict = {}
        self._fallback_data: dict = {}
        self._lang = "de"
        self._load_fallback()
        self._load("de")

    @classmethod
    def instance(cls) -> "Translator":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def language(self) -> str:
        return self._lang

    def set_language(self, lang: str):
        self._load(lang)

    def load_from_settings(self):
        """Aktive Sprache aus AppSettings laden. Sicher vor/bei DB-Initialisierung."""
        try:
            from database.db import get_session
            from database.models import AppSettings
            session = get_session()
            try:
                self._load(AppSettings.get(session, "language", "de") or "de")
            finally:
                session.close()
        except Exception:
            self._load("de")

    def _load_fallback(self):
        path = Path(__file__).parent / "de.json"
        if path.exists():
            with open(path, encoding="utf-8") as f:
                self._fallback_data = json.load(f)

    def _load(self, lang: str):
        path = Path(__file__).parent / f"{lang}.json"
        if not path.exists():
            path = Path(__file__).parent / "de.json"
            lang = "de"
        with open(path, encoding="utf-8") as f:
            self._data = json.load(f)
        self._lang = lang

    def _resolve(self, data: dict, key: str) -> Any:
        node: Any = data
        for part in key.split("."):
            if isinstance(node, dict):
                node = node.get(part)
            else:
                return None
            if node is None:
                return None
        return node

    def t(self, key: str, **kwargs) -> str:
        """Schlüssel wie 'pen.brand' auflösen. Fallback: Deutsch, dann key selbst."""
        node = self._resolve(self._data, key)
        if not isinstance(node, str):
            node = self._resolve(self._fallback_data, key)
        text = node if isinstance(node, str) else key
        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, IndexError, ValueError):
                pass
        return text

    def locale_default(self, key: str, fallback: str = "") -> str:
        """Locale-Standardwert aus der aktiven Sprach-JSON lesen."""
        node = self._data.get("locale", {})
        return node.get(key, fallback)


def t(key: str, **kwargs) -> str:
    return Translator.instance().t(key, **kwargs)


def load_language_from_settings():
    """Shortcut für den App-Start: Sprache aus der DB aktivieren."""
    Translator.instance().load_from_settings()


# ── LocaleService ─────────────────────────────────────────────────────────────

class LocaleService:
    """
    Verwaltet regionale Einstellungen (Währung, Trennzeichen, Wechselkurse).
    Liest aus AppSettings-DB; Fallback auf JSON-Defaults der aktiven Sprache.
    Singleton – einmal initialisiert, überall verfügbar.
    """
    _instance: "LocaleService | None" = None

    def __init__(self):
        self._decimal_sep: str = "."
        self._thousands_sep: str = "'"
        self._currency: str = "CHF"
        self._currency_position: str = "before"
        self._date_format: str = "DD.MM.YYYY"
        self._exchange_rates: dict[str, float] = dict(DEFAULT_EXCHANGE_RATES)
        self._load_from_db()

    @classmethod
    def instance(cls) -> "LocaleService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls):
        """Nach Einstellungsänderungen neu laden."""
        cls._instance = None

    def _load_from_db(self):
        """Lädt Einstellungen aus der Datenbank. Fallback auf JSON-Defaults."""
        try:
            from database.db import get_session
            from database.models import AppSettings
            session = get_session()
            try:
                tr = Translator.instance()
                decimal_raw = AppSettings.get(session, "locale_decimal_sep")
                if decimal_raw is None:
                    decimal_raw = tr.locale_default("decimal_sep", ".")
                thousands_raw = AppSettings.get(session, "locale_thousands_sep")
                if thousands_raw is None:
                    thousands_raw = tr.locale_default("thousands_sep", "'")
                self._decimal_sep, self._thousands_sep = normalize_number_separators(
                    decimal_raw,
                    thousands_raw,
                )
                self._currency = normalize_currency_code(
                    AppSettings.get(session, "default_currency")
                    or tr.locale_default("currency", "CHF"),
                    "CHF",
                )
                self._currency_position = (
                    AppSettings.get(session, "locale_currency_position")
                    or tr.locale_default("currency_position", "before")
                )
                self._date_format = (
                    AppSettings.get(session, "locale_date_format")
                    or tr.locale_default("date_format", "DD.MM.YYYY")
                )
                if self._date_format not in DATE_FORMAT_OPTIONS:
                    self._date_format = "DD.MM.YYYY"
                rates_json = AppSettings.get(session, "exchange_rates_json")
                if rates_json:
                    parsed_rates = json.loads(rates_json)
                    rates = dict(DEFAULT_EXCHANGE_RATES)
                    for code in SUPPORTED_CURRENCIES:
                        try:
                            value = float(parsed_rates.get(code, rates[code]))
                        except (TypeError, ValueError):
                            continue
                        if math.isfinite(value) and value > 0:
                            rates[code] = value
                    rates["CHF"] = 1.0
                    self._exchange_rates = rates
            finally:
                session.close()
        except Exception:
            pass  # DB noch nicht initialisiert → Defaults behalten

    # ── Getter ────────────────────────────────────────────────────────────────

    @property
    def decimal_sep(self) -> str:
        return self._decimal_sep

    @property
    def thousands_sep(self) -> str:
        return self._thousands_sep

    @property
    def currency(self) -> str:
        return self._currency

    @property
    def exchange_rates(self) -> dict[str, float]:
        return self._exchange_rates

    @property
    def currency_position(self) -> str:
        return self._currency_position

    @property
    def date_format(self) -> str:
        return self._date_format

    @property
    def qt_date_format(self) -> str:
        """QDateEdit-kompatibles Anzeigeformat aus dem App-Datumsformat."""
        return (
            self._date_format
            .replace("YYYY", "yyyy")
            .replace("DD", "dd")
            .replace("MM", "MM")
        )

    # ── Formatierung ─────────────────────────────────────────────────────────

    def format_number(self, value: float, decimals: int = 2, *, grouping: bool = True) -> str:
        """Zahl regional formatiert.

        ``grouping=False`` ist für editierbare Felder gedacht. Dort werden
        bewusst keine Tausendertrennzeichen eingesetzt, damit Cursorbewegung
        und Eingabe in Qt-Spinboxen stabil bleiben.
        """
        try:
            decimals = max(0, int(decimals))
            if grouping:
                raw = f"{abs(float(value)):,.{decimals}f}"
                raw = raw.replace(",", "\x00")
                raw = raw.replace(".", self._decimal_sep)
                raw = raw.replace("\x00", self._thousands_sep)
            else:
                raw = f"{abs(float(value)):.{decimals}f}".replace(".", self._decimal_sep)
            return ("-" if float(value) < 0 else "") + raw
        except (TypeError, ValueError, OverflowError):
            return str(value)

    def format_money(
        self,
        amount: Optional[float],
        currency: Optional[str] = None,
        decimals: int = 2,
    ) -> str:
        """Betrag als Währungsstring gemäß App-Region formatieren."""
        if amount is None:
            amount = 0.0
        cur = normalize_currency_code(currency, self._currency)
        num = self.format_number(amount, decimals)
        if not cur:
            return num
        if self._currency_position == "after":
            return f"{num} {cur}"
        return f"{cur} {num}"

    def format_date(self, value) -> str:
        """Datum regional formatiert. Akzeptiert date, datetime oder None."""
        if value is None:
            return "—"
        try:
            if hasattr(value, "date") and not hasattr(value, "day"):
                value = value.date()
            # datetime hat date(), date hat year/month/day direkt.
            year = int(value.year)
            month = int(value.month)
            day = int(value.day)
            return (
                self._date_format
                .replace("YYYY", f"{year:04d}")
                .replace("DD", f"{day:02d}")
                .replace("MM", f"{month:02d}")
            )
        except Exception:
            return str(value)

    def convert_to_default(self, amount: float, from_currency: str) -> float:
        """
        Betrag in die Standardwährung umrechnen.
        Weg: from_currency → CHF → Standardwährung.
        """
        source = normalize_currency_code(from_currency, self._currency)
        target = normalize_currency_code(self._currency, "CHF")
        numeric = float(amount)
        if source == target:
            return numeric
        source_rate = self._exchange_rates.get(source)
        target_rate = self._exchange_rates.get(target)
        if not source_rate or not target_rate:
            # Unknown/invalid legacy codes are treated as already being in the
            # app's default currency instead of silently applying a CHF rate.
            return numeric
        chf_amount = numeric / source_rate
        return chf_amount * target_rate

    @staticmethod
    def parse_localized_number(
        text: str,
        decimal_sep: str = ".",
        thousands_sep: str = "'",
    ) -> Optional[float]:
        """Robustes Parsen lokaler Zahlen ohne Faktor-100/1000-Fallen.

        Neben dem eingestellten Dezimalzeichen wird auch das jeweils andere
        Zeichen akzeptiert. So wird etwa ``39,96`` in einer Punkt-Region nicht
        fälschlich zu ``3996``. Enthält die Eingabe Punkt *und* Komma, gilt das
        zuletzt vorkommende Zeichen als Dezimaltrennzeichen. ISO-Währungscodes,
        Einheiten, Leerzeichen und übliche Tausenderzeichen werden toleriert.
        """
        decimal_sep, thousands_sep = normalize_number_separators(
            decimal_sep,
            thousands_sep,
        )
        if text is None:
            return None
        raw = str(text).strip()
        if not raw:
            return None

        raw = raw.replace("−", "-").replace("’", "'").replace("`", "'")
        negative_parentheses = raw.startswith("(") and raw.endswith(")")
        if negative_parentheses:
            raw = raw[1:-1]
        # Nur bekannte Währungen/Einheiten werden toleriert. Andere Zeichen
        # machen die Eingabe ungültig; so wird z. B. "1/2" nicht zu "12".
        raw = re.sub(
            r"(?i)(?:US\$|SFR\.?|CHF|FR\.?|EUR|USD|GBP|€|£|\$)",
            " ",
            raw,
        )
        raw = re.sub(r"(?i)\b(?:ml|mm|cm|kg|g|min|sec|s)\b", " ", raw)
        raw = raw.replace("\u00a0", " ").replace("\u202f", " ").strip()
        if re.search(r"[^0-9.,'\s+\-]", raw):
            return None
        if not raw:
            return None

        sign = ""
        if raw[0] in "+-":
            sign, raw = raw[0], raw[1:]
        if "+" in raw or "-" in raw:
            return None

        # Apostroph und Leerraum sind in den unterstützten Regionen nie Dezimalzeichen.
        raw = raw.replace("'", "").replace(" ", "")
        if not raw or not any(ch.isdigit() for ch in raw):
            return None

        dot_count = raw.count(".")
        comma_count = raw.count(",")

        if dot_count and comma_count:
            decimal_char = "." if raw.rfind(".") > raw.rfind(",") else ","
            grouping_char = "," if decimal_char == "." else "."
            integer_part, decimal_part = raw.rsplit(decimal_char, 1)
            if not decimal_part.isdigit():
                return None
            grouped_parts = integer_part.split(grouping_char)
            if len(grouped_parts) > 1:
                if not (
                    1 <= len(grouped_parts[0]) <= 3
                    and grouped_parts[0].isdigit()
                    and all(len(part) == 3 and part.isdigit() for part in grouped_parts[1:])
                ):
                    return None
            elif not integer_part.isdigit():
                return None
            raw = "".join(grouped_parts) + "." + decimal_part
        elif dot_count or comma_count:
            sep = "." if dot_count else ","
            count = raw.count(sep)
            groups = raw.split(sep)
            trailing_len = len(groups[-1])

            if count > 1:
                # Mehrfach dasselbe Zeichen ist nur als korrekt gruppierte
                # Ganzzahl erlaubt. Formen wie 12,34,56 werden abgelehnt statt
                # still zu 1234.56 umgedeutet zu werden.
                all_grouped = (
                    1 <= len(groups[0]) <= 3
                    and groups[0].isdigit()
                    and all(len(part) == 3 and part.isdigit() for part in groups[1:])
                )
                if not all_grouped:
                    return None
                raw = "".join(groups)
            elif sep == thousands_sep and trailing_len == 3:
                raw = "".join(groups)
            elif sep != decimal_sep and trailing_len == 3 and 1 <= len(groups[0]) <= 3:
                # Fremdes Gruppierungsformat ohne Dezimalteil, z. B. 1,234
                # in einer Schweizer Region. App-Eingabefelder haben höchstens
                # zwei Nachkommastellen; drei Ziffern sind daher Gruppierung.
                raw = "".join(groups)
            else:
                # Aktives oder alternatives Dezimalzeichen: 39,96 / 39.96.
                raw = groups[0] + "." + groups[1]

        if raw.startswith("."):
            raw = "0" + raw
        if raw.count(".") > 1 or not re.fullmatch(r"\d+(?:\.\d*)?", raw):
            return None
        try:
            value = float(("-" if negative_parentheses else sign) + raw)
        except ValueError:
            return None
        return value

    def parse_number(self, text: str) -> Optional[float]:
        """Nutzereingabe gemäß den aktiven Regionseinstellungen parsen."""
        return self.parse_localized_number(text, self._decimal_sep, self._thousands_sep)


def locale() -> LocaleService:
    """Globaler Zugriff auf den LocaleService."""
    return LocaleService.instance()


def format_money(
    amount: Optional[float],
    currency: Optional[str] = None,
    decimals: int = 2,
) -> str:
    """Shortcut für ``LocaleService.format_money``."""
    return LocaleService.instance().format_money(amount, currency, decimals)


def format_number(value: float, decimals: int = 2, *, grouping: bool = True) -> str:
    """Shortcut für ``LocaleService.format_number``."""
    return LocaleService.instance().format_number(value, decimals, grouping=grouping)


def format_date(value) -> str:
    """Shortcut für locale().format_date()."""
    return LocaleService.instance().format_date(value)
