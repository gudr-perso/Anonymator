# anonymator/files/textlayer.py
"""Couche de texte positionné : un texte plat en ordre de lecture, plus la
boîte de chaque mot. Concept du domaine, indépendant du format source — un PDF
natif l'extrait, un OCR la reconstruit depuis une image.

Aucun import de PyMuPDF ni de Pillow ici : ce module ne sait pas d'où vient la
page, seulement comment la décrire."""
from dataclasses import dataclass

from anonymator.model import Entity
from anonymator.textnorm import normalize
from anonymator.merge import merge_entities

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


# --- propagation d'une valeur confirmée à toutes ses occurrences ---

_MIN_SINGLE_TOKEN = 3


def _is_propagatable(value: str) -> bool:
    """Écarte les valeurs risquées : purement numériques, ou token unique
    trop court (fort risque de sur-détection)."""
    tokens = normalize(value).split()
    if not tokens:
        return False
    if "".join(tokens).isdigit():
        return False
    if len(tokens) == 1 and len(tokens[0]) < _MIN_SINGLE_TOKEN:
        return False
    return True


def _collect_targets(per_page_entities: list[list[Entity]]) -> dict[str, tuple[str, str]]:
    """valeur normalisée → (type, valeur canonique). Confirmées seulement.
    La valeur canonique est la première rencontrée (regroupement UI cohérent)."""
    targets: dict[str, tuple[str, str]] = {}
    for entities in per_page_entities:
        for e in entities:
            if not e.confirmed or not _is_propagatable(e.value):
                continue
            targets.setdefault(normalize(e.value), (e.type, e.value))
    return targets


def _find_occurrences(page: PageText, tokens: list[str],
                      etype: str, canonical: str) -> list[Entity]:
    """Repère les suites consécutives de WordBox dont les tokens normalisés
    égalent `tokens`. Match par mot entier (jamais par sous-chaîne)."""
    boxes = page.words
    norm = [normalize(b.text) for b in boxes]
    n = len(tokens)
    out: list[Entity] = []
    i = 0
    while n and i + n <= len(boxes):
        if norm[i:i + n] == tokens:
            out.append(Entity(etype, canonical, boxes[i].char_start,
                              boxes[i + n - 1].char_end, "propagated", 1.0, True))
            i += n
        else:
            i += 1
    return out


def propagate_across_pages(
    pages: list[PageText],
    per_page_entities: list[list[Entity]],
) -> list[list[Entity]]:
    """Réplique chaque valeur sensible confirmée à toutes ses occurrences,
    sur toutes les pages, puis fusionne avec les détections d'origine."""
    targets = _collect_targets(per_page_entities)
    result: list[list[Entity]] = []
    for page, entities in zip(pages, per_page_entities):
        extra: list[Entity] = []
        for key, (etype, canonical) in targets.items():
            extra.extend(_find_occurrences(page, key.split(), etype, canonical))
        result.append(merge_entities(entities + extra))
    return result
