from PySide6.QtCore import QThread, Signal
from anonymator.files.anonymize_file import scan_csv


class FileScanWorker(QThread):
    # Raw scan result — includes entities with confirmed=False
    scan_finished = Signal(object)  # dict[(row,col) -> list[Entity]]; Signal(object) for tuple-keyed dict
    error = Signal(str)

    def __init__(self, doc, loader, ref, cols: set[int]):
        super().__init__()
        self._doc, self._loader, self._ref, self._cols = doc, loader, ref, cols

    def run(self):
        try:
            ner = self._loader.get()   # construction du détecteur DANS le thread
            self.scan_finished.emit(scan_csv(self._doc, ner, self._ref, self._cols))
        except Exception as exc:  # noqa: BLE001 — escalated to UI via error signal
            self.error.emit(str(exc))
