from anonymator.model import Entity


def _overlaps(a: Entity, b: Entity) -> bool:
    return a.start < b.end and b.start < a.end


def _rank(e: Entity) -> tuple:
    # 1) déterministe ou règle utilisateur prioritaire  2) confiance  3) span long
    return (e.source in ("deterministic", "rule"), e.confidence, e.length)


def merge_entities(entities: list[Entity]) -> list[Entity]:
    ordered = sorted(entities, key=_rank, reverse=True)
    kept: list[Entity] = []
    for e in ordered:
        if any(_overlaps(e, k) for k in kept):
            continue
        kept.append(e)
    return sorted(kept)
