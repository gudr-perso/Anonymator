# anonymator/ui/pdf_scan_worker.py
from pathlib import Path
from PySide6.QtCore import QThread, Signal
from anonymator.files.pdf.pdf_io import scan_pdf


class PdfScanWorker(QThread):
    scan_finished = Signal(object)   # list[PageScan]
    error = Signal(str)

    def __init__(self, path: Path, ner, ref):
        super().__init__()
        self._path, self._ner, self._ref = path, ner, ref

    def run(self):
        try:
            self.scan_finished.emit(scan_pdf(self._path, self._ner, self._ref))
        except Exception as exc:   # noqa: BLE001 — remonté à l'UI via error
            self.error.emit(str(exc))
