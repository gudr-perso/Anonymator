from typing import Protocol
import re
from anonymator.model import Entity


class NerDetector(Protocol):
    def detect(self, text: str, labels: list[str]) -> list[Entity]: ...


class FakeNer:
    """NER déterministe pour les tests : mappe des chaînes exactes → type."""
    def __init__(self, mapping: dict[str, str]):
        self._mapping = mapping

    def detect(self, text: str, labels: list[str]) -> list[Entity]:
        out: list[Entity] = []
        for surface, etype in self._mapping.items():
            for m in re.finditer(re.escape(surface), text):
                out.append(Entity(etype, surface, m.start(), m.end(), "ner", 1.0))
        return sorted(out)


class NullNer:
    """Détecteur NER vide : aucune détection floue. Sert le mode dégradé
    (modèle GLiNER absent) — les règles déterministes restent actives."""
    def detect(self, text: str, labels: list[str]) -> list[Entity]:
        return []


# Carte label GLiNER (français) → code d'entité interne
_LABEL_TO_TYPE = {
    "personne": "PERSON",
    "adresse postale": "ADDRESS",
    "organisation": "ORG",
}


class GlinerDetector:
    """Adaptateur autour du modèle GLiNER. Importé paresseusement."""
    def __init__(self, model_name: str = "urchade/gliner_multi-v2.1",
                 threshold: float = 0.5):
        from gliner import GLiNER  # import paresseux : torch lourd
        self._model = GLiNER.from_pretrained(model_name)
        self._threshold = threshold

    def detect(self, text: str, labels: list[str]) -> list[Entity]:
        raw = self._model.predict_entities(text, labels,
                                            threshold=self._threshold)
        out: list[Entity] = []
        for r in raw:
            etype = _LABEL_TO_TYPE.get(r["label"], r["label"].upper())
            out.append(Entity(etype, r["text"], r["start"], r["end"],
                              "ner", float(r["score"])))
        return sorted(out)
