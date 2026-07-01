# anonymator/ui/pdf_scan_worker.py
from pathlib import Path
from PySide6.QtCore import QThread, Signal
from anonymator.files.pdf.pdf_io import scan_pdf


class PdfScanWorker(QThread):
    scan_finished = Signal(object)   # list[PageScan]
    error = Signal(str)

    def __init__(self, path: Path, loader, ref):
        super().__init__()
        self._path, self._loader, self._ref = path, loader, ref

    def run(self):
        try:
            ner = self._loader.get()   # construction du détecteur DANS le thread
            self.scan_finished.emit(scan_pdf(self._path, ner, self._ref))
        except Exception as exc:   # noqa: BLE001 — remonté à l'UI via error
            self.error.emit(str(exc))
