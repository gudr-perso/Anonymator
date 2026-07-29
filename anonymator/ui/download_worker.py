from PySide6.QtCore import QThread, Signal
from anonymator.core.model_download import download_model


class DownloadWorker(QThread):
    # (octets reçus, total ; total=0 si inconnu). « qint64 » et non `int` :
    # `Signal(int)` = int C++ 32 bits, or le dépôt du modèle pèse plus de 2 Gio.
    # Au-delà, shiboken lève un OverflowError *hors* du try/except ci-dessous
    # (il remonte à sys.excepthook) et tronque la valeur en négatif.
    progress = Signal("qint64", "qint64")
    status = Signal(str)
    download_finished = Signal()
    error = Signal(str)

    def run(self):
        try:
            download_model(
                on_progress=lambda r, t: self.progress.emit(r, t or 0),
                on_status=self.status.emit,
            )
            self.download_finished.emit()
        except Exception as exc:     # noqa: BLE001 — remonté à l'UI
            self.error.emit(str(exc))
