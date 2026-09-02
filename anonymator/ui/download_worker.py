from PySide6.QtCore import QThread, Signal
from anonymator.core.model_download import DownloadCancelled, download_model


class DownloadWorker(QThread):
    # (octets reçus, total ; total=0 si inconnu). « qint64 » et non `int` :
    # `Signal(int)` = int C++ 32 bits, or le dépôt du modèle pèse plus de 2 Gio.
    # Au-delà, shiboken lève un OverflowError *hors* du try/except ci-dessous
    # (il remonte à sys.excepthook) et tronque la valeur en négatif.
    progress = Signal("qint64", "qint64")
    status = Signal(str)
    download_finished = Signal()
    error = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cancelled = False

    def cancel(self) -> None:
        """Demande l'arrêt du téléchargement.

        Posé depuis le thread GUI, lu depuis le worker : un simple booléen
        suffit. Il est consulté à chaque incrément d'octets (cf.
        `model_download.make_tqdm_class`), donc l'arrêt survient au paquet
        suivant, pas à la fin des ~2,2 Go."""
        self._cancelled = True

    def run(self):
        try:
            download_model(
                on_progress=lambda r, t: self.progress.emit(r, t or 0),
                on_status=self.status.emit,
                should_cancel=lambda: self._cancelled,
            )
            self.download_finished.emit()
        except DownloadCancelled:
            return                   # arrêt demandé : ni succès, ni erreur
        except Exception as exc:     # noqa: BLE001 — remonté à l'UI
            self.error.emit(str(exc))
