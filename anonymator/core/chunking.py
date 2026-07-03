from anonymator.model import Entity
from anonymator.pipeline import detect
from anonymator.merge import merge_entities

# GLiNER tronque silencieusement toute entrée > ~384 tokens (≈ 1500 caractères
# de texte français dense) : au-delà, le bas du texte n'est jamais analysé et
# la détection s'effondre. On découpe donc en segments nettement sous ce seuil.
GLINER_MAX_CHARS = 1000


def chunk_spans(text: str, max_len: int) -> list[tuple[int, int]]:
    """Découpe [text] en segments <= max_len, en coupant de préférence sur le
    dernier espace avant la limite (jamais en plein mot si possible)."""
    spans, start, n = [], 0, len(text)
    while start < n:
        end = min(start + max_len, n)
        if end < n:
            cut = text.rfind(" ", start, end)
            if cut > start:
                end = cut + 1
        spans.append((start, end))
        start = end
    return spans


def detect_long(text: str, ner, ref, max_len: int = GLINER_MAX_CHARS) -> list[Entity]:
    if len(text) <= max_len:
        return detect(text, ner, ref)
    found: list[Entity] = []
    for start, end in chunk_spans(text, max_len):
        for e in detect(text[start:end], ner, ref):
            found.append(Entity(e.type, e.value, e.start + start,
                                e.end + start, e.source, e.confidence))
    return merge_entities(found)
