from anonymator.model import Entity
from anonymator.deterministic import detect_deterministic
from anonymator.merge import merge_entities
from anonymator.ner import NerDetector
from anonymator.referential import Referential

def detect(text: str, ner: NerDetector, ref: Referential) -> list[Entity]:
    det_types = ref.active_deterministic_types()
    deterministic = [e for e in detect_deterministic(text)
                     if e.type in det_types]
    labels = ref.active_ner_labels()
    ner_entities = ner.detect(text, labels) if labels else []
    ner_entities = [e for e in ner_entities if ref.is_active(e.type)]
    return merge_entities(deterministic + ner_entities)
