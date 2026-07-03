from dataclasses import dataclass
from pathlib import Path
from PySide6.QtCore import QThread, Signal
from anonymator.files.ooxml import scan, docx_io, pptx_io


@dataclass
class OoxmlScanResult:
    fmt: str                 # "docx" | "pptx"
    doc: object              # Document python-docx ou Presentation python-pptx
    units: list              # list[TextUnit] des parties principales
    scanned: dict             # dict[int, list[Entity]] (brut, incl. non confirmés)


class OoxmlScanWorker(QThread):
    scan_finished = Signal(object)   # OoxmlScanResult
    error = Signal(str)

    def __init__(self, path: Path, loader, ref):
        super().__init__()
        self._path, self._loader, self._ref = Path(path), loader, ref

    def run(self):
        try:
            ner = self._loader.get()   # construction du détecteur DANS le thread
            suffix = self._path.suffix.lower()
            if suffix == ".docx":
                from docx import Document
                doc = Document(str(self._path))
                units = list(docx_io.iter_main_units(doc))
                fmt = "docx"
            else:
                from pptx import Presentation
                doc = Presentation(str(self._path))
                units = list(pptx_io.iter_main_units(doc))
                fmt = "pptx"
            scanned = scan.scan_units(units, ner, self._ref)
            self.scan_finished.emit(OoxmlScanResult(fmt, doc, units, scanned))
        except Exception as exc:  # noqa: BLE001 — remonté à l'UI via error
            self.error.emit(str(exc))
