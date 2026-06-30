from PySide6.QtCore import QThread, Signal


class DownloadWorker(QThread):
    status = Signal(str)
    finished = Signal()
    error = Signal(str)

    def run(self):
        try:
            self.status.emit("Chargement du modèle GLiNER…")
            from anonymator.ner import GlinerDetector  # import torch différé
            GlinerDetector()                            # déclenche le téléchargement HF
            self.finished.emit()
        except Exception as exc:
            self.error.emit(str(exc))
