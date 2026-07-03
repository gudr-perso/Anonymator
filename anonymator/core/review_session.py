from anonymator.model import Entity
from anonymator.merge import merge_entities
from anonymator.anonymize import apply_masking
from anonymator.report.audit import AuditReport


class ReviewSession:
    def __init__(self, text: str, entities: list[Entity]):
        self.text = text
        self._entities = merge_entities(list(entities))
        self._enabled = [e.confirmed for e in self._entities]
        self._disabled_types: set[str] = set()

    def entities(self) -> list[Entity]:
        return list(self._entities)

    def set_entity_enabled(self, index: int, enabled: bool) -> None:
        self._enabled[index] = enabled

    def set_type_enabled(self, etype: str, enabled: bool) -> None:
        if enabled:
            self._disabled_types.discard(etype)
        else:
            self._disabled_types.add(etype)

    def add_manual(self, etype: str, start: int, end: int) -> None:
        value = self.text[start:end]
        new = Entity(etype, value, start, end, "manual", 1.0)
        self._entities = merge_entities(self._entities + [new])
        self._enabled = [e.confirmed for e in self._entities]

    def retained(self) -> list[Entity]:
        out = []
        for e, on in zip(self._entities, self._enabled):
            if on and e.type not in self._disabled_types:
                out.append(e)
        return out

    def unconfirmed(self) -> list[Entity]:
        """Entités au format valide mais clé de contrôle invalide, non masquées
        par défaut (case décochée). À surligner distinctement dans la revue avec
        la mention « non confirmé » — l'utilisateur peut cocher pour masquer.
        Exclut celles que l'utilisateur a déjà cochées (→ retenues) ou dont le
        type est désactivé."""
        out = []
        for e, on in zip(self._entities, self._enabled):
            if not on and not e.confirmed and e.type not in self._disabled_types:
                out.append(e)
        return out

    def masked_text(self, ref) -> str:
        return apply_masking(self.text, self.retained(), ref)

    def report(self, ref) -> AuditReport:
        rep = AuditReport()
        for e in self.retained():
            rep.add(e.type, e.value, ref.tag_for(e.type), "texte")
        return rep
