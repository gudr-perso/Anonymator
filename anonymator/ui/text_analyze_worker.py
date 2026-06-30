from PySide6.QtCore import QThread, Signal
from anonymator.core.chunking import detect_long


class TextAnalyzeWorker(QThread):
    """Détection NER hors du thread UI : charge le modèle + analyse le texte."""
    done = Signal(str, object)   # (texte analysé, list[Entity])
    error = Signal(str)

    def __init__(self, text, loader, ref):
        super().__init__()
        self._text, self._loader, self._ref = text, loader, ref

    def run(self):
        try:
            ner = self._loader.get()
            ents = detect_long(self._text, ner, self._ref)
            self.done.emit(self._text, ents)
        except Exception as exc:  # noqa: BLE001 — escaladé à l'UI via le signal error
            self.error.emit(str(exc))
