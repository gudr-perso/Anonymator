from anonymator.model import Entity
from anonymator.referential import Referential
from anonymator.core.risk import risk_level

REF = Referential.load_default()

def _e(t):
    return Entity(t, "x", 0, 1, "deterministic")

def test_high_when_any_haute():
    assert risk_level([_e("PERSON")], REF) == "Élevé"

def test_medium_when_moyenne_only():
    assert risk_level([_e("ORG")], REF) == "Moyen"

def test_low_when_empty_or_basse():
    assert risk_level([], REF) == "Faible"
    assert risk_level([_e("POSTAL_CODE")], REF) == "Faible"
