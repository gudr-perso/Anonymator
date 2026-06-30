from PySide6.QtCore import QThread, Signal


class DownloadWorker(QThread):
    status = Signal(str)
    download_finished = Signal()
    error = Signal(str)

    def run(self):
        try:
            self.status.emit("Chargement du modèle GLiNER…")
            from anonymator.ner import GlinerDetector  # import torch différé
            # Warms the HuggingFace cache. ModelLoader will load from cache on first use.
            GlinerDetector()
            self.download_finished.emit()
        except Exception as exc:
            self.error.emit(str(exc))
