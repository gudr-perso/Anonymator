from anonymator.model import Entity
from anonymator.referential import Referential

_ORDER = {"Haute": 3, "Moyenne": 2, "Basse": 1}


def risk_level(entities: list[Entity], ref: Referential) -> str:
    """Niveau de risque d'après la plus haute sensibilité parmi les entités retenues."""
    top = max((_ORDER.get(ref.sensitivity_for(e.type), 1) for e in entities), default=0)
    if top >= 3:
        return "Élevé"
    if top == 2:
        return "Moyen"
    return "Faible"
