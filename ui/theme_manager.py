"""Designprofile fuer FPM - nach dem Vorbild von BudgetManager und
FreizeitManager.

Warum es diese Datei gibt: FPM fuehrte seine Farben bis hierher als Literale
im Stylesheet und in rund 150 Inline-Aufrufen. Ein Designprofil liess sich
dadurch nur nachtraeglich per Textersetzung aufpraegen - und traf dabei
zwangslaeufig nur die Literale, die jemand vorher eingetragen hatte. Alles
Uebrige blieb hell: weisse Karten auf dunklem Grund, graue Schrift auf
grauem Grund.

Aufbau bewusst identisch zu den Schwestermodulen:

* Im Code stehen nur zwei Rueckfallprofile (hell und dunkel). Alles Weitere
  kommt als JSON aus ``ui/profiles`` und wird mitgeliefert.
* Eigene Fassungen des Nutzers landen im Datenordner und ueberschreiben das
  mitgelieferte Profil, ohne es zu zerstoeren.
* Ein fehlerhaftes Profil wird uebersprungen und protokolliert, statt die
  Anwendung farblos starten zu lassen.
* Laeuft FPM im LifePlanner, hat das dort zentral gesetzte Profil Vorrang -
  sofern der Nutzer das nicht abwaehlt.
"""
from __future__ import annotations

import json
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_log = logging.getLogger(__name__)

MODE_LIGHT = "hell"
MODE_DARK = "dunkel"
MODES = (MODE_LIGHT, MODE_DARK)

FONT_SIZE_MIN = 8
FONT_SIZE_MAX = 22
DEFAULT_FONT_SIZE = 10

_HEX = re.compile(r"#[0-9a-fA-F]{6}")

# Einstellungsschluessel in app_settings.
SETTING_THEME = "ui.theme"
SETTING_FOLLOW_SHARED = "ui.theme_follow_shared"


def is_hex_color(value: Any) -> bool:
    return isinstance(value, str) and bool(_HEX.fullmatch(value.strip()))


def slugify(name: str) -> str:
    text = str(name or "").strip().lower()
    for source, target in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss"),
                           ("–", "-"), ("—", "-")):
        text = text.replace(source, target)
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^a-z0-9_\-]", "", text).replace("-", "_")
    return re.sub(r"_+", "_", text).strip("_") or "profil"


# Vollstaendiger Schluesselsatz. Ein Profil darf Schluessel weglassen - dann
# gilt der Wert des Rueckfallprofils gleicher Helligkeit. Aeltere und von Hand
# geschriebene Profile bleiben so gueltig, wenn spaeter Schluessel dazukommen.
COLOR_KEYS = (
    "hintergrund_app", "hintergrund_panel", "hintergrund_seitenleiste",
    "seitenleiste_text", "seitenleiste_text_gedimmt", "seitenleiste_aktiv",
    "text", "text_gedimmt", "text_invers",
    "akzent", "akzent_text", "akzent_hover",
    "rand", "eingabe_hintergrund",
    "tabelle_hintergrund", "tabelle_alt", "tabelle_header", "tabelle_header_text",
    "tabelle_gitter", "auswahl_hintergrund", "auswahl_text",
    "hover_hintergrund", "hover_text",
    "karte_hintergrund", "karte_rand",
    "erfolg", "erfolg_text", "warnung", "warnung_text", "gefahr", "gefahr_text",
    "gedaempft", "gedaempft_text",
    # FPM-eigene Bedeutungsfarben. Sie stehen fuer die vier Kacheln des
    # Dashboards und die Statusfarben der Sammlung - das Gegenstueck zu den
    # Budget-Typfarben im BudgetManager.
    "bereich_sammlung", "bereich_rotation", "bereich_service", "bereich_aktivitaet",
)

BUILTIN_PROFILES: dict[str, dict[str, Any]] = {
    "Standard - Hell": {
        "modus": MODE_LIGHT,
        "hintergrund_app": "#f0f3f7",
        "hintergrund_panel": "#ffffff",
        "hintergrund_seitenleiste": "#0b1220",
        "seitenleiste_text": "#f8fafc",
        "seitenleiste_text_gedimmt": "#94a3b8",
        "seitenleiste_aktiv": "#1d4ed8",
        "text": "#1e2a38",
        "text_gedimmt": "#5f6f72",
        "text_invers": "#ffffff",
        "akzent": "#2563eb",
        "akzent_text": "#ffffff",
        "akzent_hover": "#1d4ed8",
        "rand": "#d5dce6",
        "eingabe_hintergrund": "#ffffff",
        "tabelle_hintergrund": "#ffffff",
        "tabelle_alt": "#f7f9fc",
        "tabelle_header": "#f8fafc",
        "tabelle_header_text": "#475569",
        "tabelle_gitter": "#d5dce6",
        "auswahl_hintergrund": "#dbeafe",
        "auswahl_text": "#0f172a",
        "hover_hintergrund": "#e8f1ff",
        "hover_text": "#0f172a",
        "karte_hintergrund": "#ffffff",
        "karte_rand": "#dbe3ec",
        "erfolg": "#27ae60",
        "erfolg_text": "#ffffff",
        "warnung": "#f39c12",
        "warnung_text": "#ffffff",
        "gefahr": "#e74c3c",
        "gefahr_text": "#ffffff",
        "gedaempft": "#7f8c8d",
        "gedaempft_text": "#ffffff",
        "bereich_sammlung": "#8e44ad",
        "bereich_rotation": "#d35400",
        "bereich_service": "#c0392b",
        "bereich_aktivitaet": "#2563eb",
        "schriftgroesse": DEFAULT_FONT_SIZE,
    },
    "Standard - Dunkel": {
        "modus": MODE_DARK,
        "hintergrund_app": "#0f172a",
        "hintergrund_panel": "#1e293b",
        "hintergrund_seitenleiste": "#020617",
        "seitenleiste_text": "#e2e8f0",
        "seitenleiste_text_gedimmt": "#94a3b8",
        "seitenleiste_aktiv": "#2563eb",
        "text": "#e2e8f0",
        "text_gedimmt": "#94a3b8",
        "text_invers": "#0f172a",
        "akzent": "#3b82f6",
        "akzent_text": "#ffffff",
        "akzent_hover": "#60a5fa",
        "rand": "#334155",
        "eingabe_hintergrund": "#1e293b",
        "tabelle_hintergrund": "#1e293b",
        "tabelle_alt": "#243044",
        "tabelle_header": "#0f172a",
        "tabelle_header_text": "#94a3b8",
        "tabelle_gitter": "#334155",
        "auswahl_hintergrund": "#1d4ed8",
        "auswahl_text": "#ffffff",
        "hover_hintergrund": "#1e3a8a",
        "hover_text": "#e2e8f0",
        "karte_hintergrund": "#1e293b",
        "karte_rand": "#334155",
        # Bedeutungsfarben werden im Dunklen aufgehellt: Ein sattes Rot auf
        # dunklem Grund liest sich schlecht, ein helleres traegt die Bedeutung
        # genauso.
        "erfolg": "#22c55e",
        "erfolg_text": "#052e16",
        "warnung": "#eab308",
        "warnung_text": "#1c1917",
        "gefahr": "#ef4444",
        "gefahr_text": "#ffffff",
        "gedaempft": "#94a3b8",
        "gedaempft_text": "#0f172a",
        "bereich_sammlung": "#c084fc",
        "bereich_rotation": "#fb923c",
        "bereich_service": "#f87171",
        "bereich_aktivitaet": "#60a5fa",
        "schriftgroesse": DEFAULT_FONT_SIZE,
    },
}

DEFAULT_PROFILE = "Standard - Hell"

# Umbenannte Profile: alte Einstellung weiterhin aufloesen.
ALIASES: dict[str, str] = {
    # Dieselben Designs trugen in den Programmen verschiedene Namen - wer im
    # LifePlanner "Kontrast - Schwarz/Weiss" waehlte, fand hier nur
    # "Kontrast Schwarzweiss" und bekam deshalb ein halb uebernommenes Design.
    # Ab jetzt gilt der Name des Hosts; gespeicherte Einstellungen loesen
    # weiterhin auf.
    "Standard Hell": "Standard - Hell",
    "Standard Dunkel": "Standard - Dunkel",
    "Kontrast Schwarzweiss": "Kontrast - Schwarz/Weiß",
    "Warm Sepia - Hell": "Hell - Warm (Sepia)",
    "OLED Schwarz": "Dunkel - OLED (Kontrastarm)",
}


@dataclass
class ThemeProfile:
    name: str
    data: dict[str, Any]

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    @property
    def mode(self) -> str:
        return str(self.data.get("modus", MODE_LIGHT)).strip().lower()

    @property
    def is_dark(self) -> bool:
        return self.mode == MODE_DARK

    @property
    def font_size(self) -> int:
        try:
            size = int(self.data.get("schriftgroesse", DEFAULT_FONT_SIZE))
        except (TypeError, ValueError):
            size = DEFAULT_FONT_SIZE
        return max(FONT_SIZE_MIN, min(FONT_SIZE_MAX, size))

    @property
    def scale(self) -> float:
        """Schriftgroesse als FPM-Skalierungsfaktor; 10 bedeutet unveraendert."""
        return max(0.85, min(1.50, self.font_size / float(DEFAULT_FONT_SIZE)))

    def color(self, key: str) -> str:
        """Farbe mit Rueckfall auf das Standardprofil derselben Helligkeit."""
        value = self.data.get(key)
        if is_hex_color(value):
            return str(value).strip()
        fallback = BUILTIN_PROFILES["Standard - Dunkel" if self.is_dark else "Standard - Hell"]
        return str(fallback.get(key, "#808080"))

    def to_dict(self) -> dict[str, Any]:
        return dict(self.data)


def validate_profile_data(data: dict[str, Any]) -> tuple[bool, str]:
    """Prueft ein Profil, bevor es angeboten wird."""
    mode = str(data.get("modus", MODE_LIGHT)).strip().lower()
    if mode not in MODES:
        return False, f"Invalid modus: {mode!r} (allowed: {', '.join(MODES)})"

    raw_size = data.get("schriftgroesse", DEFAULT_FONT_SIZE)
    try:
        size = int(raw_size)
    except (TypeError, ValueError):
        return False, f"Invalid schriftgroesse: {raw_size!r}"
    if not FONT_SIZE_MIN <= size <= FONT_SIZE_MAX:
        return False, f"schriftgroesse outside {FONT_SIZE_MIN}-{FONT_SIZE_MAX}: {size}"

    for key, value in data.items():
        if key in ("modus", "schriftgroesse") or key.startswith("_"):
            continue
        if isinstance(value, str) and value.strip().startswith("#") and not is_hex_color(value):
            return False, f"Invalid color {key}={value!r}"
    return True, ""


class ThemeManager:
    """Singleton. Kennt alle Profile und das aktive."""

    _instance: ThemeManager | None = None

    def __init__(self) -> None:
        self._bundled: dict[str, Path] = {}
        self._user: dict[str, Path] = {}
        self._errors: list[tuple[str, str, str]] = []
        self._current: ThemeProfile | None = None
        self.rescan()

    @classmethod
    def instance(cls) -> ThemeManager:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Nur fuer Tests und nach einem Profilwechsel."""
        cls._instance = None

    # ── Ablageorte ───────────────────────────────────────────────────────────
    @staticmethod
    def bundled_dir() -> Path:
        """Mitgelieferte Profile - im Quellbaum wie im gebauten Paket."""
        bundle = getattr(sys, "_MEIPASS", "")
        if bundle:
            packed = Path(bundle) / "ui" / "profiles"
            if packed.is_dir():
                return packed
        return Path(__file__).resolve().parent / "profiles"

    @staticmethod
    def user_dir() -> Path:
        from logic.log_utils import data_dir
        target = data_dir() / "theme_profiles"
        target.mkdir(parents=True, exist_ok=True)
        return target

    # ── Einlesen ─────────────────────────────────────────────────────────────
    def rescan(self) -> None:
        self._bundled, self._user, self._errors = {}, {}, []
        self._scan(self.bundled_dir(), self._bundled)
        try:
            self._scan(self.user_dir(), self._user)
        except OSError as exc:
            _log.warning("User theme profiles are not readable: %s", exc)

    def _scan(self, directory: Path, target: dict[str, Path]) -> None:
        if not directory.is_dir():
            return
        for file in sorted(directory.glob("*.json")):
            name = file.stem.replace("_", " ").strip()
            try:
                raw = json.loads(file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                self._record_error(name, file, f"JSON load error: {exc}")
                continue
            if not isinstance(raw, dict):
                self._record_error(name, file, "Profile is not a JSON object")
                continue
            name = str(raw.get("name") or "").strip() or name
            data = {k: v for k, v in raw.items() if k != "name"}
            ok, message = validate_profile_data(data)
            if not ok:
                self._record_error(name, file, message)
                continue
            target[name] = file

    def _record_error(self, name: str, path: Path, message: str) -> None:
        """Fehlerhafte Profile werden uebersprungen, nicht verschwiegen."""
        self._errors.append((name, str(path), message))
        _log.warning("Theme profile skipped: %s (%s): %s", name, path, message)

    def get_load_errors(self) -> list[tuple[str, str, str]]:
        return list(self._errors)

    # ── Profile ──────────────────────────────────────────────────────────────
    def available_profiles(self) -> list[str]:
        names = set(self._bundled) | set(self._user) | set(BUILTIN_PROFILES)
        names -= set(ALIASES)
        return sorted(names, key=str.casefold)

    def _resolve(self, name: str) -> str:
        return ALIASES.get(str(name or "").strip(), str(name or "").strip())

    def is_bundled(self, name: str) -> bool:
        return self._resolve(name) in self._bundled

    def has_override(self, name: str) -> bool:
        return self._resolve(name) in self._user

    def get_profile(self, name: str) -> ThemeProfile | None:
        """Reihenfolge: eigene Fassung, dann mitgeliefert, dann eingebaut."""
        name = self._resolve(name)
        for index in (self._user, self._bundled):
            path = index.get(name)
            if path is None:
                continue
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                self._record_error(name, path, f"JSON load error: {exc}")
                continue
            return ThemeProfile(name, {k: v for k, v in raw.items() if k != "name"})
        if name in BUILTIN_PROFILES:
            return ThemeProfile(name, dict(BUILTIN_PROFILES[name]))
        return None

    # ── Auswahl ──────────────────────────────────────────────────────────────
    def current_name(self) -> str:
        from database.db import get_session
        from database.models import AppSettings
        session = get_session()
        try:
            return self._resolve(AppSettings.get(session, SETTING_THEME, DEFAULT_PROFILE)
                                 or DEFAULT_PROFILE)
        finally:
            session.close()

    def follows_shared(self) -> bool:
        """Uebernimmt FPM das gemeinsame Theme des LifePlanners?

        Standard ist ja. Ist die Datenbank noch nicht offen - etwa beim ersten
        Stylesheet-Aufbau -, gilt ebenfalls der Standard: das Hostprofil selbst
        braucht keine Datenbank, nur diese Frage.
        """
        from sqlalchemy.exc import SQLAlchemyError

        from database.db import get_session
        from database.models import AppSettings
        try:
            # get_session wirft RuntimeError, solange init_db nicht gelaufen ist.
            session = get_session()
        except RuntimeError:
            return True
        try:
            return str(AppSettings.get(session, SETTING_FOLLOW_SHARED, "1")) not in ("0", "false")
        except SQLAlchemyError:
            # Die Datei ist da, die Tabelle noch nicht - beim ersten Start.
            return True
        finally:
            session.close()

    def set_follows_shared(self, value: bool) -> None:
        from database.db import get_session
        from database.models import AppSettings
        session = get_session()
        try:
            AppSettings.set(session, SETTING_FOLLOW_SHARED, "1" if value else "0")
        finally:
            session.close()
        self._current = None

    def shared_profile(self) -> ThemeProfile | None:
        """Das Profil des Hosts als vollwertiges Themeprofil - oder None."""
        from ui.host_theme import load_host_theme
        data = load_host_theme()
        if data is None:
            return None
        name = str(data.get("name", "")).strip()
        # Kennt FPM das Profil selbst, hat die eigene Fassung Vorrang: sie ist
        # vollstaendig, die uebergebenen Farben sind nur ein Auszug.
        local = self.get_profile(name)
        if local is not None:
            return local
        payload = host_theme_as_profile_data(data)
        ok, message = validate_profile_data(payload)
        if not ok:
            _log.warning("Shared theme %r is invalid: %s", name, message)
            return None
        return ThemeProfile(name, payload)

    def current_profile(self) -> ThemeProfile:
        """Immer ein gueltiges Profil - notfalls das eingebaute helle.

        Reihenfolge: gemeinsames Theme des Hosts (wenn eingeschaltet und
        vorhanden), sonst die lokale Wahl, sonst das eingebaute helle Profil.
        """
        from sqlalchemy.exc import SQLAlchemyError

        if self._current is not None:
            return self._current

        profile = None
        if self.follows_shared():
            # Das Hostprofil kommt aus einer Datei und steht auch dann zur
            # Verfuegung, wenn die Datenbank noch nicht offen ist.
            profile = self.shared_profile()

        settled = True
        if profile is None:
            try:
                profile = self.get_profile(self.current_name())
            except (RuntimeError, SQLAlchemyError) as exc:
                # Beim ersten Stylesheet-Aufbau ist die Datenbank noch zu.
                # Dann gilt das Standardprofil - aber es wird NICHT gemerkt,
                # sonst bliebe die Sitzung darauf stehen, obwohl der Nutzer
                # laengst ein anderes gewaehlt hat.
                _log.debug("Theme selection not readable yet: %s", exc)
                settled = False

        if profile is None:
            profile = ThemeProfile(DEFAULT_PROFILE, dict(BUILTIN_PROFILES[DEFAULT_PROFILE]))
        if settled:
            self._current = profile
        return profile

    def set_current(self, name: str) -> ThemeProfile:
        """Waehlt das Theme lokal aus und merkt es sich."""
        from database.db import get_session
        from database.models import AppSettings
        profile = self.get_profile(name)
        if profile is None:
            raise ValueError(f"Unknown theme: {name!r}")
        session = get_session()
        try:
            AppSettings.set(session, SETTING_THEME, profile.name)
        finally:
            session.close()
        self._current = profile
        return profile

    def reset_to_default(self) -> ThemeProfile:
        """Zurueck auf den Auslieferungszustand des Programms."""
        return self.set_current(DEFAULT_PROFILE)

    # ── Eigene Fassungen ─────────────────────────────────────────────────────
    def save_override(self, name: str, data: dict[str, Any]) -> Path:
        """Speichert eine eigene Fassung. Das Mitgelieferte bleibt unberuehrt."""
        name = self._resolve(name)
        ok, message = validate_profile_data(data)
        if not ok:
            raise ValueError(message)
        payload = {"name": name, **data}
        path = self.user_dir() / f"{slugify(name)}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
        self.rescan()
        if self._current is not None and self._current.name == name:
            self._current = self.get_profile(name)
        return path

    def reset_override(self, name: str) -> bool:
        """Eigene Fassung verwerfen und zum mitgelieferten Stand zurueck."""
        name = self._resolve(name)
        path = self._user.get(name)
        if path is None:
            return False
        path.unlink(missing_ok=True)
        self.rescan()
        if self._current is not None and self._current.name == name:
            self._current = self.get_profile(name)
        return True


def host_theme_as_profile_data(data: dict[str, Any]) -> dict[str, Any]:
    """Uebersetzt ``lifeplanner.theme.v1`` in ein FPM-Profil.

    Der Host liefert einen Auszug an Rollen. Was fehlt, faellt ueber
    ``ThemeProfile.color`` auf das Standardprofil derselben Helligkeit
    zurueck - deshalb wird hier nur uebernommen, was wirklich da ist.
    """
    colors = data.get("farben")
    payload: dict[str, Any] = {
        "modus": MODE_DARK if str(data.get("modus", "")).strip().lower() == MODE_DARK
        else MODE_LIGHT,
    }
    size = data.get("schriftgroesse")
    if size is not None:
        try:
            payload["schriftgroesse"] = max(FONT_SIZE_MIN, min(FONT_SIZE_MAX, int(size)))
        except (TypeError, ValueError):
            pass
    if isinstance(colors, dict):
        for key, value in colors.items():
            if key in COLOR_KEYS and is_hex_color(value):
                payload[key] = str(value).strip()
    return payload
