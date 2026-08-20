"""Bild-Downloads ohne die Oberfläche einzufrieren (v0.2.88).

Bisher lief ``download_image_bytes()`` synchron im GUI-Thread: Bei einem
hängenden Server stand die App bis zum Timeout still. Hier läuft der Download
in einem ``QThread``; ein modaler Fortschrittsdialog hält die Oberfläche
lebendig und erlaubt Abbrechen.

Die eigentliche Netz- und Prüflogik bleibt in ``logic/media_storage_service``
(rein, testbar). Dieses Modul ist nur die Qt-Hülle.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal, Qt
from PySide6.QtWidgets import QProgressDialog, QWidget

from i18n.translator import t
from logic.media_storage_service import (
    DownloadCancelledError,
    ImageDownloadOperation,
)


class _DownloadWorker(QObject):
    finished = Signal(object, str)   # (bytes | None, suffix)
    failed = Signal(str)

    def __init__(self, url: str, timeout_s: int | None = None):
        super().__init__()
        kwargs = {} if timeout_s is None else {"timeout_s": timeout_s}
        self._operation = ImageDownloadOperation(url, **kwargs)

    def cancel(self) -> None:
        # Thread-safe: sets an event and closes the active response socket.
        self._operation.cancel()

    def run(self) -> None:
        try:
            data, suffix = self._operation.download()
        except DownloadCancelledError as exc:
            self.failed.emit(str(exc))
            return
        except Exception as exc:  # noqa: BLE001 - an die GUI weiterreichen
            self.failed.emit(str(exc))
            return
        self.finished.emit(data, suffix)


def download_image_with_progress(
    parent: QWidget | None,
    url: str,
    *,
    timeout_s: int | None = None,
) -> tuple[bytes, str]:
    """Lädt ein Bild im Hintergrund und zeigt derweil einen Abbruch-Dialog.

    Gibt ``(daten, suffix)`` zurück oder wirft die ursprüngliche Fehlermeldung
    als ``ValueError``. Bei Abbruch durch den Nutzer wird ebenfalls geworfen –
    die Aufrufer behandeln jeden Fehler bereits nicht-fatal (v0.2.87).
    """
    thread = QThread()
    worker = _DownloadWorker(url, timeout_s)
    worker.moveToThread(thread)

    result: dict = {}

    def _ok(data, suffix):
        result["data"] = data
        result["suffix"] = suffix
        thread.quit()

    def _err(message: str):
        result["error"] = message
        thread.quit()

    thread.started.connect(worker.run)
    worker.finished.connect(_ok)
    worker.failed.connect(_err)

    dialog = QProgressDialog(t("media.download_progress"), t("common.cancel"), 0, 0, parent)
    dialog.setWindowModality(Qt.WindowModality.WindowModal)
    dialog.setMinimumDuration(300)
    dialog.setAutoClose(False)
    dialog.setAutoReset(False)

    def _cancel():
        result.setdefault("error", t("media.download_cancelled"))
        # Direct thread-safe call: a queued Qt slot would not run while the
        # worker blocks inside its download method.
        worker.cancel()

    dialog.canceled.connect(_cancel)
    thread.finished.connect(dialog.close)

    thread.start()
    dialog.exec()
    # cancel() closes the response; wait until the worker has actually exited.
    # This prevents a live QThread from surviving dialog/app shutdown.
    if thread.isRunning():
        worker.cancel()
        thread.quit()
        if not thread.wait(10_000):
            raise RuntimeError(t("media.download_shutdown_failed"))
    worker.deleteLater()
    thread.deleteLater()

    if "error" in result or "data" not in result:
        raise ValueError(result.get("error") or t("media.download_cancelled"))
    return result["data"], result["suffix"]


def download_image_to(
    parent: QWidget | None,
    url: str,
    target: Path,
) -> Path:
    """Wie oben, schreibt aber direkt und korrigiert die Endung."""
    data, detected = download_image_with_progress(parent, url)
    if target.suffix.lower() != detected and not (
        detected == ".jpg" and target.suffix.lower() in (".jpg", ".jpeg")
    ):
        target = target.with_suffix(detected)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return target
