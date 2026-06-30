from anonymator.model import Entity
from anonymator.merge import merge_entities
from anonymator.referential import Referential


def apply_masking(text: str, entities: list[Entity],
                  ref: Referential) -> str:
    """Remplace chaque span retenu par l'étiquette de son type.

    Les entités sont d'abord passées dans merge_entities pour éliminer
    tout chevauchement (idempotent sur une liste déjà fusionnée), puis
    remplacées de la fin vers le début pour préserver les offsets.
    """
    for e in sorted(merge_entities(entities), key=lambda e: e.start, reverse=True):
        text = text[:e.start] + ref.tag_for(e.type) + text[e.end:]
    return text
