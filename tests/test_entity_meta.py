from anonymator.ui.entity_meta import ENTITY_META, EntityMeta
from anonymator.ui.settings_screen import _TYPES  # liste source des 14 codes

def test_all_types_have_meta():
    for code in _TYPES:
        assert code in ENTITY_META, f"métadonnée manquante : {code}"
        m = ENTITY_META[code]
        assert isinstance(m, EntityMeta)
        assert m.label and m.subtitle and m.icon

def test_person_meta():
    m = ENTITY_META["PERSON"]
    assert m.label == "PERSON"
    assert m.subtitle == "Noms et prénoms de personnes"
    assert m.icon == "person"
