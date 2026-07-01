from anonymator.ner import NerDetector


class ModelLoader:
    """Charge GlinerDetector à la demande (import torch différé). Injectable
    pour les tests via un détecteur fourni."""

    def __init__(self, detector: NerDetector | None = None):
        self._detector = detector

    def has_detector(self) -> bool:
        """True si un détecteur est déjà disponible (injecté), sans charger GLiNER."""
        return self._detector is not None

    def get(self) -> NerDetector:
        if self._detector is None:
            from anonymator.ner import GlinerDetector
            self._detector = GlinerDetector()
        return self._detector
