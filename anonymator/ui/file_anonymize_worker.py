# anonymator/ui/file_anonymize_worker.py
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import QThread, Signal
from anonymator.files.anonymize_file import anonymize_file


class FileAnonymizeWorker(QThread):
    """Anonymisation directe (sans revue) hors du thread UI : construit le
    détecteur DANS le thread, puis anonymise et écrit le fichier."""
    done = Signal(object)    # FileResult
    error = Signal(str)

    def __init__(self, path: Path, loader, ref, out_dir: Path, when: datetime):
        super().__init__()
        self._path, self._loader, self._ref = path, loader, ref
        self._out_dir, self._when = out_dir, when

    def run(self):
        try:
            ner = self._loader.get()   # construction du détecteur DANS le thread
            result = anonymize_file(self._path, ner, self._ref,
                                    self._out_dir, self._when)
            self.done.emit(result)
        except Exception as exc:   # noqa: BLE001 — remonté à l'UI via error
            self.error.emit(str(exc))
