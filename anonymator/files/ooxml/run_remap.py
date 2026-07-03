from anonymator.model import Entity
from anonymator.merge import merge_entities
from anonymator.referential import Referential


def build_offsets(runs) -> tuple[str, list[tuple[int, int, int]]]:
    """Texte concaténé + table [(index_run, char_start, char_end)].
    Un run vide occupe 0 caractère. Symétrique de pdf/mapping.py."""
    parts, spans, pos = [], [], 0
    for i, run in enumerate(runs):
        t = run.text or ""
        spans.append((i, pos, pos + len(t)))
        parts.append(t)
        pos += len(t)
    return "".join(parts), spans


def apply(runs, entities: list[Entity], ref: Referential) -> None:
    """Masque chaque span en préservant la mise en forme des runs non touchés.
    Mute `runs` en place.

    On traite de la fin vers le début : un remplacement n'affecte que le
    suffixe du texte, donc les offsets (absolus) des entités plus à gauche
    restent valides. On recalcule les offsets à chaque entité car la longueur
    des runs change après masquage (peu d'entités par paragraphe → négligeable).
    """
    for e in sorted(merge_entities(entities), key=lambda e: e.start, reverse=True):
        if e.end <= e.start:      # span vide : rien à masquer (garde-fou)
            continue
        _, spans = build_offsets(runs)
        _mask_span(runs, spans, e.start, e.end, ref.tag_for(e.type))


def _mask_span(runs, spans, s: int, e: int, tag: str) -> None:
    touched = [(i, a, b) for (i, a, b) in spans if a < e and s < b]
    if not touched:
        return
    first = True
    for (i, a, b) in touched:
        lo = max(s, a) - a          # offset relatif au début du run
        hi = min(e, b) - a
        t = runs[i].text or ""
        if first:
            runs[i].text = t[:lo] + tag + t[hi:]
            first = False
        else:
            runs[i].text = t[:lo] + t[hi:]
