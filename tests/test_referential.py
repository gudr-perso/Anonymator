from anonymator.referential import Referential

def test_loads_default_referential():
    ref = Referential.load_default()
    assert ref.tag_for("EMAIL") == "[EMAIL]"
    assert ref.is_active("EMAIL") is True
    assert ref.is_active("URL") is False

def test_active_ner_labels_maps_codes_to_french_labels():
    ref = Referential.load_default()
    assert set(ref.active_ner_labels()) == {"personne", "adresse postale", "organisation"}

def test_active_deterministic_types_excludes_inactive():
    ref = Referential.load_default()
    types = ref.active_deterministic_types()
    assert "EMAIL" in types and "URL" not in types
