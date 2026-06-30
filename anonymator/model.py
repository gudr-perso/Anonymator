from dataclasses import dataclass


@dataclass(frozen=True)
class Entity:
    type: str          # code du référentiel, ex. "EMAIL", "PERSON"
    value: str         # texte exact détecté
    start: int         # offset caractère inclusif
    end: int           # offset caractère exclusif
    source: str        # "deterministic" | "ner"
    confidence: float = 1.0

    @property
    def length(self) -> int:
        return self.end - self.start

    def __lt__(self, other: "Entity") -> bool:
        return (self.start, self.length) < (other.start, other.length)
