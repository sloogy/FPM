"""
Übersetzungssystem – lädt JSON-Dateien, stellt t() und LocaleService bereit.

v0.2.17 – Locale-System:
- LocaleService liest regional settings aus AppSettings (DB).
- Fallback auf Locale-Defaults der aktiven Sprach-JSON.
- format_money() und format_number() für einheitliche Darstellung.
- Regionsvoreinstellungen: CH, DE, AT, FR, GB, US.
"""
import json
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
                self._currency = (
                    AppSettings.get(session, "default_currency")
                    or tr.locale_default("currency", "CHF")
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

    def format_number(self, value: float, decimals: int = 2) -> str:
        """Zahl regional formatiert (Trennzeichen aus Settings)."""
        try:
            raw = f"{abs(value):,.{decimals}f}"           # immer Punkt + Komma-Tausender
            raw = raw.replace(",", "\x00")                 # Tausender temp. ersetzen
            raw = raw.replace(".", self._decimal_sep)      # Dezimalpunkt setzen
            raw = raw.replace("\x00", self._thousands_sep) # Tausender setzen
            return ("-" if value < 0 else "") + raw
        except Exception:
            return str(value)

    def format_money(self, amount: Optional[float], currency: Optional[str] = None) -> str:
        """
        Betrag als Währungsstring formatieren.
        currency=None → Standardwährung aus Settings.
        """
        if amount is None:
            amount = 0.0
        cur = currency or self._currency
        num = self.format_number(amount, 2)
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
        chf_amount = amount / self._exchange_rates.get(from_currency, 1.0)
        return chf_amount * self._exchange_rates.get(self._currency, 1.0)

    def parse_number(self, text: str) -> Optional[float]:
        """
        Nutzereingabe mit regionalem Trennzeichen parsen.
        Versteht sowohl Punkt als auch Komma als Dezimalzeichen.
        """
        if not text or not text.strip():
            return None
        t = text.strip()
        # Wenn Dezimaltrennzeichen Komma ist: Punkte als Tausender entfernen, Komma → Punkt
        if self._decimal_sep == ",":
            t = t.replace(".", "").replace(",", ".")
        else:
            t = t.replace(",", "")
        try:
            return float(t)
        except ValueError:
            return None


def locale() -> LocaleService:
    """Globaler Zugriff auf den LocaleService."""
    return LocaleService.instance()


def format_money(amount: Optional[float], currency: Optional[str] = None) -> str:
    """Shortcut für locale().format_money()."""
    return LocaleService.instance().format_money(amount, currency)


def format_number(value: float, decimals: int = 2) -> str:
    """Shortcut für locale().format_number()."""
    return LocaleService.instance().format_number(value, decimals)


def format_date(value) -> str:
    """Shortcut für locale().format_date()."""
    return LocaleService.instance().format_date(value)
