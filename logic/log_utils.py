"""Production logging, crash diagnostics and privacy-safe support bundles."""
from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import platform
import re
import sys
import threading
import uuid
import zipfile

_LOGGER_NAME = "fpm"
_CONFIGURED = False
_QT_HANDLER = None


class _PrivacyFilter(logging.Filter):
    """Redact common local paths and credential-like values from log records."""

    _secret = re.compile(
        r"(?i)(token|password|passwd|secret|authorization|api[_-]?key)\s*[:=]\s*([^\s,;]+)"
    )

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
            home = str(Path.home())
            if home:
                message = message.replace(home, "~")
            message = self._secret.sub(r"\1=<redacted>", message)
            record.msg = message
            record.args = ()
        except (OSError, TypeError, ValueError):
            pass
        return True


def data_dir() -> Path:
    override = os.environ.get("FPM_DATA_DIR")
    path = Path(override).expanduser() if override else Path.home() / ".fpm_data"
    path.mkdir(parents=True, exist_ok=True)
    return path


def diagnostics_dir() -> Path:
    path = data_dir() / "diagnostics"
    path.mkdir(parents=True, exist_ok=True)
    return path


def log_file_path() -> Path:
    path = diagnostics_dir() / "fpm.log"
    return path


def configure_logging(*, level: int = logging.INFO) -> Path:
    global _CONFIGURED
    path = log_file_path()
    if _CONFIGURED:
        return path

    root = logging.getLogger()
    root.setLevel(level)
    handler = RotatingFileHandler(
        path,
        maxBytes=1_500_000,
        backupCount=5,
        encoding="utf-8",
        delay=True,
    )
    handler.setLevel(level)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(threadName)s | %(message)s"
        )
    )
    handler.addFilter(_PrivacyFilter())
    root.addHandler(handler)
    _CONFIGURED = True
    logging.getLogger(_LOGGER_NAME).info("Logging initialisiert: %s", path)
    return path


def new_error_id() -> str:
    return uuid.uuid4().hex[:10].upper()


def log_unexpected(context: str, exc: BaseException, *, error_id: str | None = None) -> str:
    """Log an unexpected exception and return a support-friendly error ID."""
    configure_logging()
    error_id = error_id or new_error_id()
    logging.getLogger("fpm.unexpected").exception(
        "Fehler-ID %s | Unerwarteter Fehler in %s: %s",
        error_id,
        context,
        exc,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return error_id


def _global_excepthook(exc_type, exc, tb) -> None:
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc, tb)
        return
    error_id = new_error_id()
    configure_logging()
    logging.getLogger("fpm.crash").critical(
        "Fehler-ID %s | Unbehandelter Hauptthread-Fehler",
        error_id,
        exc_info=(exc_type, exc, tb),
    )
    print(
        f"FountainPen Manager ist unerwartet beendet worden. Fehler-ID: {error_id}\n"
        f"Diagnose: {log_file_path()}",
        file=sys.stderr,
    )


def _threading_excepthook(args) -> None:
    error_id = new_error_id()
    configure_logging()
    logging.getLogger("fpm.crash.thread").critical(
        "Fehler-ID %s | Unbehandelter Thread-Fehler in %s",
        error_id,
        getattr(args.thread, "name", "?"),
        exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
    )


def install_global_exception_hooks() -> None:
    sys.excepthook = _global_excepthook
    if hasattr(threading, "excepthook"):
        threading.excepthook = _threading_excepthook


def install_qt_message_handler() -> None:
    """Forward Qt warnings/errors to the rotating production log."""
    global _QT_HANDLER
    try:
        from PySide6.QtCore import QtMsgType, qInstallMessageHandler
    except (ImportError, ModuleNotFoundError):
        return

    levels = {
        QtMsgType.QtDebugMsg: logging.DEBUG,
        QtMsgType.QtInfoMsg: logging.INFO,
        QtMsgType.QtWarningMsg: logging.WARNING,
        QtMsgType.QtCriticalMsg: logging.ERROR,
        QtMsgType.QtFatalMsg: logging.CRITICAL,
    }

    def _handler(msg_type, context, message):
        category = getattr(context, "category", None) or "qt"
        logging.getLogger(f"fpm.qt.{category}").log(
            levels.get(msg_type, logging.INFO), "%s", message
        )

    _QT_HANDLER = _handler
    qInstallMessageHandler(_QT_HANDLER)


def create_diagnostics_bundle(destination: Path) -> Path:
    """Export logs and environment metadata without database or user media."""
    configure_logging()
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "python": sys.version,
        "platform": platform.platform(),
        "executable": Path(sys.executable).name,
        "frozen": bool(getattr(sys, "frozen", False)),
    }
    try:
        from app_info import APP_NAME, APP_VERSION, APP_BUILD

        metadata.update({"app": APP_NAME, "version": APP_VERSION, "build": APP_BUILD})
    except (ImportError, AttributeError):
        metadata["app"] = "FountainPen Manager"

    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "environment.json", json.dumps(metadata, indent=2, ensure_ascii=False)
        )
        archive.writestr(
            "README.txt",
            "Dieses Paket enthält nur technische Logs und Systemmetadaten. "
            "Datenbank, Sammlungsdaten und Medien werden nicht exportiert.\n",
        )
        for candidate in sorted(diagnostics_dir().glob("fpm.log*")):
            if candidate.is_file():
                archive.write(candidate, arcname=f"logs/{candidate.name}")
    return destination
