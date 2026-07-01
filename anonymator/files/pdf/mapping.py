# anonymator/files/pdf/mapping.py
from anonymator.model import Entity
from anonymator.files.pdf.extract import PageText, WordBox

Rect = tuple[float, float, float, float]


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
