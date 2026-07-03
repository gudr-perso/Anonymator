from anonymator.model import Entity
from anonymator.pipeline import detect

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


class _ChunkingNer:
    """Enveloppe un NerDetector : découpe le texte en segments courts avant de
    le passer au modèle (GLiNER tronque > ~384 tokens), puis rebase les offsets.

    Seul le NER est découpé. La détection déterministe (IBAN, NIR, téléphone…)
    voit le texte entier : ces entités contiennent des espaces et seraient
    scindées par une frontière de chunk (un IBAN coupé en deux n'est plus
    reconnu)."""
    def __init__(self, inner, max_len: int):
        self._inner, self._max_len = inner, max_len

    def detect(self, text: str, labels: list[str]) -> list[Entity]:
        if len(text) <= self._max_len:
            return self._inner.detect(text, labels)
        out: list[Entity] = []
        for start, end in chunk_spans(text, self._max_len):
            for e in self._inner.detect(text[start:end], labels):
                out.append(Entity(e.type, e.value, e.start + start,
                                  e.end + start, e.source, e.confidence))
        return out


def detect_long(text: str, ner, ref, max_len: int = GLINER_MAX_CHARS) -> list[Entity]:
    # Le déterministe tourne sur le texte entier ; seul le NER est découpé.
    return detect(text, _ChunkingNer(ner, max_len), ref)
