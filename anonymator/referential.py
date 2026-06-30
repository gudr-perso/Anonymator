import json
from pathlib import Path
from anonymator.textnorm import normalize

_TYPE_TO_NER_LABEL = {
    "PERSON": "personne",
    "ADDRESS": "adresse postale",
    "ORG": "organisation",
}
_DEFAULT_PATH = Path(__file__).parent / "config" / "entities.json"
_STOPLIST_PATH = Path(__file__).parent / "config" / "ner_stoplist.json"


class Referential:
    def __init__(self, entries: list[dict],
                 overrides: dict[str, bool] | None = None,
                 stoplist: list[str] | None = None):
        self._by_code = {e["code"]: e for e in entries}
        self._overrides = overrides or {}
        self._stoplist = stoplist or []

    @classmethod
    def load_default(cls, overrides: dict[str, bool] | None = None) -> "Referential":
        data = json.loads(_DEFAULT_PATH.read_text(encoding="utf-8"))
        stoplist: list[str] = []
        if _STOPLIST_PATH.exists():
            stoplist = json.loads(_STOPLIST_PATH.read_text(encoding="utf-8"))
        return cls(data["entities"], overrides=overrides, stoplist=stoplist)

    def tag_for(self, code: str) -> str:
        return self._by_code[code]["tag"]

    def label_for(self, code: str) -> str:
        """Libellé lisible du type (repli sur le code si absent)."""
        return self._by_code.get(code, {}).get("label", code)

    def is_active(self, code: str) -> bool:
        if code in self._overrides:
            return self._overrides[code]
        return self._by_code.get(code, {}).get("active", False)

    def active_ner_labels(self) -> list[str]:
        return [_TYPE_TO_NER_LABEL[c] for c in self._by_code
                if self._by_code[c]["method"] == "ner" and self.is_active(c)
                and c in _TYPE_TO_NER_LABEL]

    def active_deterministic_types(self) -> set[str]:
        return {c for c, e in self._by_code.items()
                if e["method"] == "deterministic" and self.is_active(c)}

    def ner_stoplist(self) -> set[str]:
        return {normalize(t) for t in self._stoplist}

    def sensitivity_for(self, code: str) -> str:
        return self._by_code.get(code, {}).get("sensitivity", "Basse")

    def with_stoplist(self, terms: list[str]) -> "Referential":
        """Copie avec une stoplist remplacée (édition utilisateur)."""
        return Referential(list(self._by_code.values()), self._overrides, terms)
