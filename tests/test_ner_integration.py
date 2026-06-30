import pytest
from anonymator.ner import GlinerDetector


@pytest.mark.integration
def test_gliner_detects_person_and_address():
    ner = GlinerDetector()
    text = "Jean-Pierre Lefèvre habite 14 rue des Acacias à Toulouse."
    out = ner.detect(text, ["personne", "adresse postale", "organisation"])
    types = {e.type for e in out}
    assert "PERSON" in types
    # le span personne doit recouvrir le nom
    person = next(e for e in out if e.type == "PERSON")
    assert "Lefèvre" in text[person.start:person.end]
