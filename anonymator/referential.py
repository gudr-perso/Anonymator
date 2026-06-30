import json
from pathlib import Path

_TYPE_TO_NER_LABEL = {
    "PERSON": "personne",
    "ADDRESS": "adresse postale",
    "ORG": "organisation",
}
_DEFAULT_PATH = Path(__file__).parent / "config" / "entities.json"

class Referential:
    def __init__(self, entries: list[dict]):
        self._by_code = {e["code"]: e for e in entries}

    @classmethod
    def load_default(cls) -> "Referential":
        data = json.loads(_DEFAULT_PATH.read_text(encoding="utf-8"))
        return cls(data["entities"])

    def tag_for(self, code: str) -> str:
        return self._by_code[code]["tag"]

    def is_active(self, code: str) -> bool:
        return self._by_code.get(code, {}).get("active", False)

    def active_ner_labels(self) -> list[str]:
        return [_TYPE_TO_NER_LABEL[c] for c, e in self._by_code.items()
                if e["method"] == "ner" and e["active"] and c in _TYPE_TO_NER_LABEL]

    def active_deterministic_types(self) -> set[str]:
        return {c for c, e in self._by_code.items()
                if e["method"] == "deterministic" and e["active"]}
