# anonymator/files/textlayer.py
"""Couche de texte positionné : un texte plat en ordre de lecture, plus la
boîte de chaque mot. Concept du domaine, indépendant du format source — un PDF
natif l'extrait, un OCR la reconstruit depuis une image.

Aucun import de PyMuPDF ni de Pillow ici : ce module ne sait pas d'où vient la
page, seulement comment la décrire."""
from dataclasses import dataclass

from anonymator.model import Entity

Rect = tuple[float, float, float, float]


@dataclass
class WordBox:
    text: str
    rect: Rect          # (x0, y0, x1, y1) dans l'unité de la source
    char_start: int     # offset inclusif dans le texte plat
    char_end: int       # offset exclusif


@dataclass
class PageText:
    page_index: int
    text: str           # texte plat reconstruit en ordre de lecture
    words: list[WordBox]


@dataclass
class PageScan:
    page_index: int
    text: str
    words: list[WordBox]
    entities: list[Entity]


def _intersects(word: WordBox, start: int, end: int) -> bool:
    """Vrai si la plage de caractères du mot recoupe [start, end)."""
    return word.char_start < end and start < word.char_end


def rects_for_entity(page: PageText, entity: Entity) -> list[Rect]:
    """Rectangles de tous les mots dont la plage recoupe [entity.start, entity.end).
    Une entité multi-lignes produit naturellement plusieurs rectangles."""
    return [w.rect for w in page.words
            if _intersects(w, entity.start, entity.end)]


def rects_for_entities(page: PageText, entities: list[Entity]) -> list[Rect]:
    out: list[Rect] = []
    for e in entities:
        for r in rects_for_entity(page, e):
            if r not in out:
                out.append(r)
    return out
