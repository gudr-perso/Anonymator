from anonymator.model import Entity
from anonymator.referential import Referential


def apply_masking(text: str, entities: list[Entity],
                  ref: Referential) -> str:
    # remplacer de la fin vers le début pour préserver les offsets
    for e in sorted(entities, key=lambda e: e.start, reverse=True):
        text = text[:e.start] + ref.tag_for(e.type) + text[e.end:]
    return text
