# anonymator/ui/image_scan_worker.py
"""Analyse d'une image dans un fil séparé.

Deux chargements lourds y sont faits, et pas avant : le moteur OCR (32 Mo de
modèles) et le détecteur GLiNER. Les construire sur le thread principal
gèlerait la fenêtre plusieurs secondes et ferait disparaître leurs erreurs —
c'est exactement le bug « rien ne se passe » corrigé côté PDF."""
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from anonymator.files.image import image_io


class ImageScanWorker(QThread):
    scan_finished = Signal(object)   # list[PageScan]
    error = Signal(str)              # message métier, affichable tel quel

    def __init__(self, path: Path, ocr_provider, loader, ref):
        super().__init__()
        self._path = Path(path)
        self._ocr_provider = ocr_provider
        self._loader = loader
        self._ref = ref

    def run(self):
        try:
            ocr = self._ocr_provider()          # construction DANS le thread
            ner = self._loader.get()            # idem
            pages = image_io.scan_image(self._path, ocr, ner, self._ref)
        except (image_io.UnsupportedImageFormat,
                image_io.CorruptImageError) as exc:
            self.error.emit(str(exc))
            return
        except Exception as exc:                # noqa: BLE001 — remonté à l'UI
            self.error.emit(str(exc))
            return
        self.scan_finished.emit(pages)
