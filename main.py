"""
FountainPen Manager – Einstiegspunkt
Starte mit:  python main.py
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))


def _dispatch_update_cli() -> None:
    """Updater-Einstieg fuer PyInstaller/frozen Builds.

    Der Update-Dialog startet die gleiche EXE mit diesen Flags. In der
    Source-Variante wird stattdessen ``python -m updater...`` genutzt.
    """
    if "--check-update" in sys.argv:
        from updater.check_update import main as check_update_main

        raise SystemExit(check_update_main())
    if "--apply-update" in sys.argv:
        from updater.apply_update import main as apply_update_main

        raise SystemExit(apply_update_main())


_dispatch_update_cli()


def _missing_package_message(package: str) -> str:
    return (
        f"Fehlendes Python-Paket: {package}\n\n"
        "Bitte im Projektordner ausführen:\n"
        "  python -m venv .venv\n"
        "  source .venv/bin/activate\n"
        "  python -m pip install -U pip\n"
        "  python -m pip install -r requirements.txt\n\n"
        "Falls nur dieses Paket fehlt:\n"
        f"  python -m pip install {package}\n"
    )


try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QFont, QGuiApplication
    from PySide6.QtCore import Qt
except ModuleNotFoundError as exc:
    print(_missing_package_message(exc.name or "PySide6"), file=sys.stderr)
    raise SystemExit(1) from exc

try:
    import sqlalchemy  # noqa: F401 - expliziter Dependency-Check für klare Fehlermeldung
except ModuleNotFoundError as exc:
    print(_missing_package_message(exc.name or "SQLAlchemy"), file=sys.stderr)
    raise SystemExit(1) from exc

try:
    from database.db import init_db
    from ui.main_window import MainWindow
    from ui.ui_scale import apply_ui_scaling
    from i18n.translator import load_language_from_settings
    from i18n.qt_i18n import install_qt_i18n_hooks
    from app_info import APP_NAME, APP_VERSION, ORG_NAME
except Exception as exc:
    print(
        "Startfehler in den App-Modulen. Das ist wahrscheinlich ein Code-/Importfehler, "
        "nicht ein fehlendes pip-Paket.\n",
        file=sys.stderr,
    )
    traceback.print_exc()
    raise SystemExit(1) from exc


def main() -> None:
    try:
        QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    except Exception:
        pass
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(ORG_NAME)

    app.setFont(QFont("Segoe UI", 10))
    # Datenbank initialisieren (nutzt konfigurierbaren Pfad aus ~/.fpm_data/config.json)
    init_db()
    # Sprache erst nach init_db laden, damit AppSettings verfügbar ist.
    load_language_from_settings()
    install_qt_i18n_hooks()
    apply_ui_scaling(app)

    window = MainWindow()
    window.show()
    # App-Tour/Onboarding beim ersten Start (leere DB)
    window.show_onboarding_if_needed()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
