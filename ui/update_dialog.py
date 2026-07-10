"""Geführter Update-Dialog fuer FountainPen Manager.

Prueft das GitHub-Manifest, laedt das passende Asset herunter und startet den
externen Apply-Prozess. Fuer Installer-Installationen wird das Setup-Asset
bevorzugt, fuer Portable-Builds das portable ZIP.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QProcess, Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from app_info import APP_VERSION, app_version_label
from i18n.translator import t
from updater.common import clear_check_result, read_check_result

GITHUB_RELEASES_URL = "https://github.com/sloogy/FPM/releases"


def _entrypoint_cmd(module: str | None = None) -> list[str]:
    if getattr(sys, "frozen", False):
        if module == "updater.check_update":
            return [sys.executable, "--check-update"]
        if module == "updater.apply_update":
            return [sys.executable, "--apply-update"]
        return [sys.executable]
    return [sys.executable, "-m", module or "updater.check_update"]


class UpdateDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("update.title"))
        self.setMinimumSize(640, 440)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        self._proc: QProcess | None = None
        self._available = False
        self._busy = False

        root = QVBoxLayout(self)
        root.setSpacing(10)

        self.lbl_info = QLabel(t("update.current_version", version=app_version_label()))
        self.lbl_info.setWordWrap(True)
        root.addWidget(self.lbl_info)

        self.lbl_status = QLabel(t("update.status_checking"))
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setStyleSheet("font-weight: 600;")
        root.addWidget(self.lbl_status)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        root.addWidget(self.progress)

        self.btn_details = QPushButton(t("update.show_details"))
        self.btn_details.setCheckable(True)
        self.btn_details.setFlat(True)
        self.btn_details.toggled.connect(self._toggle_details)
        root.addWidget(self.btn_details, 0, Qt.AlignmentFlag.AlignLeft)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setVisible(False)
        self.log.setMaximumHeight(180)
        root.addWidget(self.log)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(line)

        btn_row = QHBoxLayout()
        self.btn_recheck = QPushButton(t("update.btn_check"))
        self.btn_recheck.clicked.connect(self._check)
        btn_row.addWidget(self.btn_recheck)

        self.btn_github = QPushButton(t("update.btn_releases"))
        self.btn_github.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(GITHUB_RELEASES_URL)))
        btn_row.addWidget(self.btn_github)

        btn_row.addStretch(1)

        self.btn_update = QPushButton(t("update.btn_update_now"))
        self.btn_update.setDefault(True)
        self.btn_update.setEnabled(False)
        self.btn_update.clicked.connect(self._apply)
        btn_row.addWidget(self.btn_update)

        self.btn_close = QPushButton(t("update.btn_close"))
        self.btn_close.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_close)
        root.addLayout(btn_row)

        self._append(t("update.hint_github_placeholder"))
        QTimer.singleShot(0, self._check)

    def _append(self, text: str) -> None:
        for line in str(text).splitlines():
            self.log.append(line)

    def _toggle_details(self, on: bool) -> None:
        self.log.setVisible(on)
        self.btn_details.setText(t("update.hide_details") if on else t("update.show_details"))

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.progress.setVisible(busy)
        self.btn_recheck.setEnabled(not busy)
        self.btn_update.setEnabled((not busy) and self._available)
        self.btn_close.setEnabled(not busy)

    def _check(self) -> None:
        if self._busy:
            return
        clear_check_result()
        self._available = False
        self.btn_update.setEnabled(False)
        self.lbl_status.setText(t("update.status_checking"))
        cmd = _entrypoint_cmd("updater.check_update") + ["--gui"]
        self._append("$ " + " ".join(cmd))
        self._set_busy(True)

        self._proc = QProcess(self)
        if not getattr(sys, "frozen", False):
            self._proc.setWorkingDirectory(str(Path(__file__).resolve().parents[1]))
        self._proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self._proc.readyReadStandardOutput.connect(self._on_output)
        self._proc.finished.connect(self._on_check_finished)
        self._proc.start(cmd[0], cmd[1:])

    def _on_output(self) -> None:
        if not self._proc:
            return
        data = bytes(self._proc.readAllStandardOutput()).decode(errors="replace")
        if data:
            self._append(data)

    def _on_check_finished(self, exit_code: int, _status) -> None:
        self._proc = None
        self._set_busy(False)
        res = read_check_result()
        remote = res.get("remote") or ""
        if res.get("available") and res.get("staged"):
            self._available = True
            self.lbl_status.setText(t("update.status_available", version=remote))
            self.btn_update.setEnabled(True)
            self.btn_update.setFocus()
        elif res.get("error"):
            self._available = False
            self.lbl_status.setText(t("update.status_error", error=res.get("error")))
        elif res:
            self._available = False
            self.lbl_status.setText(t("update.status_uptodate", version=res.get("current") or APP_VERSION))
        else:
            self._available = False
            self.lbl_status.setText(t("update.status_check_failed", code=exit_code))

    def _apply(self) -> None:
        if not self._available:
            return
        if QMessageBox.question(self, t("update.confirm_apply_title"), t("update.confirm_apply_text")) != QMessageBox.StandardButton.Yes:
            return

        cmd = _entrypoint_cmd("updater.apply_update")
        self._append("$ " + " ".join(cmd))
        self._append(t("update.status_applying"))
        try:
            if getattr(sys, "frozen", False):
                started = QProcess.startDetached(cmd[0], cmd[1:])
            else:
                started = QProcess.startDetached(cmd[0], cmd[1:], str(Path(__file__).resolve().parents[1]))
            if not started:
                raise RuntimeError("QProcess.startDetached returned False")
        except Exception as exc:
            QMessageBox.critical(self, t("update.error_title"), t("update.apply_start_failed", error=str(exc)))
            return

        self.lbl_status.setText(t("update.status_applying"))
        if self.parent() is not None:
            try:
                self.parent().close()
            except Exception:
                pass
        self.accept()
        app = QApplication.instance()
        if app is not None:
            QTimer.singleShot(0, app.quit)
