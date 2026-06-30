from PySide6.QtCore import QThread, Signal
from anonymator.files.anonymize_file import scan_csv


class FileScanWorker(QThread):
    scan_finished = Signal(object)   # dict[tuple[int,int], list[Entity]]
    error = Signal(str)

    def __init__(self, doc, ner, ref, cols):
        super().__init__()
        self._doc, self._ner, self._ref, self._cols = doc, ner, ref, cols

    def run(self):
        try:
            self.scan_finished.emit(scan_csv(self._doc, self._ner, self._ref, self._cols))
        except Exception as exc:                      # noqa: BLE001 — remonté à l'UI
            self.error.emit(str(exc))
