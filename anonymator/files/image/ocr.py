# anonymator/files/image/ocr.py
"""Moteur OCR derrière un protocole, sur le modèle de anonymator/ner.py.

Le protocole permet trois choses : tester toute la chaîne hors ligne avec
FakeOcr, offrir un mode dégradé avec NullOcr (tracé manuel seul), et changer de
moteur sans toucher au reste du code."""
from dataclasses import dataclass
from typing import Protocol

Rect = tuple[float, float, float, float]


@dataclass(frozen=True)
class OcrBox:
    text: str
    rect: Rect          # rectangle englobant, en pixels de l'image source
    confidence: float

    @classmethod
    def from_quad(cls, text: str, quad, confidence: float) -> "OcrBox":
        """Réduit un quadrilatère (4 coins) à son rectangle englobant.

        Un englobant déborde toujours un peu : en caviardage, déborder est sûr,
        rogner ne l'est pas."""
        xs = [float(p[0]) for p in quad]
        ys = [float(p[1]) for p in quad]
        return cls(text, (min(xs), min(ys), max(xs), max(ys)), float(confidence))


class OcrEngine(Protocol):
    def read(self, image) -> list[OcrBox]: ...


class FakeOcr:
    """Moteur déterministe pour les tests : rend les boîtes qu'on lui donne."""
    def __init__(self, boxes: list[OcrBox]):
        self._boxes = list(boxes)

    def read(self, image) -> list[OcrBox]:
        return list(self._boxes)


class NullOcr:
    """Moteur vide : aucune lecture. Sert le mode dégradé (dépendance OCR
    absente) — le tracé manuel de zones reste disponible."""
    def read(self, image) -> list[OcrBox]:
        return []
