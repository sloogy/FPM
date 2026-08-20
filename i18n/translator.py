"""
Übersetzungssystem – lädt JSON-Dateien, stellt t() und LocaleService bereit.

v0.2.17 – Locale-System:
- LocaleService liest regional settings aus AppSettings (DB).
- Fallback auf Locale-Defaults der aktiven Sprach-JSON.
- format_money() und format_number() für einheitliche Darstellung.
- Regionsvoreinstellungen: CH, DE, AT, FR, GB, US.
"""
import json
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
DEFAULT_EXCHANGE_RATES: dict[str, float] = {
    "CHF": 1.0,
    "EUR": 0.95,
    "USD": 1.08,
    "GBP": 0.81,
}

SUPPORTED_CURRENCIES: tuple[str, ...] = tuple(DEFAULT_EXCHANGE_RATES)

_CURRENCY_ALIASES = {
    "CHF": "CHF",
    "FR": "CHF",
    "FR.": "CHF",
    "SFR": "CHF",
    "SFR.": "CHF",
    "EUR": "EUR",
    "€": "EUR",
    "USD": "USD",
    "$": "USD",
    "US$": "USD",
    "GBP": "GBP",
    "£": "GBP",
}


def normalize_currency_code(value: str | None, fallback: str = "CHF") -> str:
    """Normalisiert unterstützte Währungsangaben auf stabile ISO-Codes."""
    normalized = str(value or "").strip().upper()
    resolved = _CURRENCY_ALIASES.get(normalized)
    if resolved:
        return resolved
    fallback_normalized = str(fallback or "CHF").strip().upper()
    return _CURRENCY_ALIASES.get(fallback_normalized, "CHF")


def normalize_number_separators(decimal: str, thousands: str) -> tuple[str, str]:
    """Liefert ein eindeutiges, unterstütztes Paar von Zahlentrennzeichen."""
    if decimal not in {".", ","}:
        return ".", "'"
    if thousands not in {"", ".", ",", "'", " "}:
        thousands = "'" if decimal == "." else "."
    if thousands == decimal:
        thousands = ""
    return decimal, thousands


def _fail_if_bad_groups(raw: str) -> bool:
    """Return ``True`` for malformed apostrophe/space digit grouping.

    Apostrophes and spaces are unambiguous grouping characters in the
    supported locales.  Validate them before stripping them so inputs such as
    ``12'34`` cannot silently become ``1234``.
    """
    grouping_chars = {char for char in raw if char == "'" or char.isspace()}
    if not grouping_chars:
        return False
    if "'" in grouping_chars and any(char.isspace() for char in grouping_chars):
        return True

    groups = re.split(r"['\s]+", raw)
    if len(groups) < 2 or not groups[0].lstrip("+-").isdigit():
        return True
    if not 1 <= len(groups[0].lstrip("+-")) <= 3:
        return True

    for index, group in enumerate(groups[1:], start=1):
        if index < len(groups) - 1:
            if len(group) != 3 or not group.isdigit():
                return True
            continue
        integer_tail = re.split(r"[.,]", group, maxsplit=1)[0]
        if len(integer_tail) != 3 or not integer_tail.isdigit():
            return True
    return False


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
                self._decimal_sep = (
                    AppSettings.get(session, "locale_decimal_sep")
                    or tr.locale_default("decimal_sep", ".")
                )
                self._thousands_sep = (
                    AppSettings.get(session, "locale_thousands_sep")
                    or tr.locale_default("thousands_sep", "'")
                )
                self._decimal_sep, self._thousands_sep = normalize_number_separators(
                    self._decimal_sep,
                    self._thousands_sep,
                )
                self._currency = (
                    AppSettings.get(session, "default_currency")
                    or tr.locale_default("currency", "CHF")
                )
                self._currency = normalize_currency_code(self._currency, "CHF")
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
                    self._exchange_rates = {
                        **DEFAULT_EXCHANGE_RATES,
                        **json.loads(rates_json),
                    }
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
    def currency_position(self) -> str:
        return self._currency_position

    @property
    def exchange_rates(self) -> dict[str, float]:
        return self._exchange_rates

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

    def format_number(
        self,
        value: float,
        decimals: int = 2,
        *,
        grouping: bool = True,
    ) -> str:
        """Zahl regional formatiert (Trennzeichen aus Settings)."""
        try:
            numeric = float(value)
            template = f"{{:,.{decimals}f}}" if grouping else f"{{:.{decimals}f}}"
            raw = template.format(abs(numeric))
            raw = raw.replace(",", "\x00")
            raw = raw.replace(".", self._decimal_sep)
            raw = raw.replace("\x00", self._thousands_sep)
            return ("-" if numeric < 0 else "") + raw
        except (TypeError, ValueError, OverflowError):
            return str(value)

    def format_money(
        self,
        amount: Optional[float],
        currency: Optional[str] = None,
        decimals: int = 2,
    ) -> str:
        """
        Betrag als Währungsstring formatieren.
        currency=None → Standardwährung aus Settings.
        """
        if amount is None:
            amount = 0.0
        cur = normalize_currency_code(currency, self._currency)
        num = self.format_number(amount, decimals)
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

    def convert_to_default(self, amount: float, from_currency: str | None) -> float:
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
            return numeric
        chf_amount = numeric / source_rate
        return chf_amount * target_rate

    @staticmethod
    def parse_localized_number(
        text: str,
        decimal_sep: str = ".",
        thousands_sep: str = "'",
    ) -> Optional[float]:
        """Parst lokale Zahlen ohne Faktor-100/1000-Fehlinterpretationen."""
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
        raw = re.sub(
            r"(?i)(?:US\$|SFR\.?|CHF|FR\.?|EUR|USD|GBP|€|£|\$)",
            " ",
            raw,
        )
        raw = re.sub(r"(?i)\b(?:ml|mm|cm|kg|g|min|sec|s)\b", " ", raw)
        raw = raw.replace("\u00a0", " ").replace("\u202f", " ").strip()
        if re.search(r"[^0-9.,'\s+\-]", raw) or not raw:
            return None
        if _fail_if_bad_groups(raw):
            return None

        sign = ""
        if raw[0] in "+-":
            sign, raw = raw[0], raw[1:]
        if "+" in raw or "-" in raw:
            return None

        raw = raw.replace("'", "").replace(" ", "")
        if not raw or not any(char.isdigit() for char in raw):
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
                valid_grouping = (
                    1 <= len(grouped_parts[0]) <= 3
                    and grouped_parts[0].isdigit()
                    and all(
                        len(part) == 3 and part.isdigit()
                        for part in grouped_parts[1:]
                    )
                )
                if not valid_grouping:
                    return None
            elif not integer_part.isdigit():
                return None
            raw = "".join(grouped_parts) + "." + decimal_part
        elif dot_count or comma_count:
            separator = "." if dot_count else ","
            groups = raw.split(separator)
            trailing_len = len(groups[-1])
            if len(groups) > 2:
                valid_grouping = (
                    1 <= len(groups[0]) <= 3
                    and groups[0].isdigit()
                    and all(len(part) == 3 and part.isdigit() for part in groups[1:])
                )
                if not valid_grouping:
                    return None
                raw = "".join(groups)
            elif separator == thousands_sep and trailing_len == 3:
                raw = "".join(groups)
            elif (
                separator != decimal_sep
                and trailing_len == 3
                and 1 <= len(groups[0]) <= 3
            ):
                raw = "".join(groups)
            else:
                raw = groups[0] + "." + groups[1]

        if raw.startswith("."):
            raw = "0" + raw
        if raw.count(".") > 1 or not re.fullmatch(r"\d+(?:\.\d*)?", raw):
            return None
        try:
            return float(("-" if negative_parentheses else sign) + raw)
        except ValueError:
            return None

    def parse_number(self, text: str) -> Optional[float]:
        """Nutzereingabe robust parsen – unabhängig von der App-Region.

        v0.2.94: Der frühere Parser entfernte bei Dezimal=Komma alle Punkte
        und bei Dezimal=Punkt alle Kommata. Damit wurde ``39,96`` in einer
        Punkt-Region zu ``3996`` (Faktor-100-Fehler, gemeldeter Bug). Jetzt
        wird das Dezimaltrennzeichen am *letzten* Vorkommen von Punkt oder
        Komma erkannt; das jeweils andere Zeichen gilt als Gruppierung und
        muss dann konsistent dreistellig gruppiert sein. Mehrdeutige oder
        fehlerhaft gruppierte Eingaben (``12,34,56``) werden abgelehnt.
        """
        return self.parse_localized_number(
            text,
            self._decimal_sep,
            self._thousands_sep,
        )


def locale() -> LocaleService:
    """Globaler Zugriff auf den LocaleService."""
    return LocaleService.instance()


def format_money(
    amount: Optional[float],
    currency: Optional[str] = None,
    decimals: int = 2,
) -> str:
    """Shortcut für locale().format_money()."""
    return LocaleService.instance().format_money(amount, currency, decimals)


def format_number(value: float, decimals: int = 2, *, grouping: bool = True) -> str:
    """Shortcut für locale().format_number()."""
    return LocaleService.instance().format_number(value, decimals, grouping=grouping)


def format_date(value) -> str:
    """Shortcut für locale().format_date()."""
    return LocaleService.instance().format_date(value)
