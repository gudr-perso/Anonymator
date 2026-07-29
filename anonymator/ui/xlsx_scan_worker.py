from pathlib import Path
from PySide6.QtCore import QThread, Signal
from anonymator.files import xlsx_io


class XlsxScanWorker(QThread):
    """Lecture, classification et scan d'un classeur, hors thread UI.

    Un classeur de 100 000 lignes ne se lit pas sur le thread d'affichage :
    openpyxl à lui seul y prendrait plusieurs secondes, fenêtre gelée."""

    scan_finished = Signal(object)   # XlsxScanResult
    error = Signal(str)

    def __init__(self, path, loader, ref,
                 header_overrides: dict[str, bool] | None = None):
        super().__init__()
        self._path, self._loader, self._ref = Path(path), loader, ref
        self._headers = dict(header_overrides or {})

    def run(self):
        try:
            ner = self._loader.get()   # construction du détecteur DANS le thread
            self.scan_finished.emit(
                xlsx_io.scan_workbook(self._path, ner, self._ref, self._headers))
        except Exception as exc:  # noqa: BLE001 — remonté à l'UI via error
            self.error.emit(str(exc))
