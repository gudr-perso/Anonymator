from anonymator.model import Entity
from anonymator.deterministic import detect_deterministic
from anonymator.secrets_detect import detect_secrets
from anonymator.merge import merge_entities
from anonymator.ner import NerDetector
from anonymator.referential import Referential
from anonymator.textnorm import normalize


def detect(text: str, ner: NerDetector, ref: Referential) -> list[Entity]:
    deterministic = [e for e in detect_deterministic(text) if ref.is_active(e.type)]
    secrets = [e for e in detect_secrets(text) if ref.is_active(e.type)]
    labels = ref.active_ner_labels()
    ner_entities = ner.detect(text, labels) if labels else []
    stop = ref.ner_stoplist()
    ner_entities = [e for e in ner_entities
                    if ref.is_active(e.type) and normalize(e.value) not in stop]
    return merge_entities(deterministic + secrets + ner_entities)
