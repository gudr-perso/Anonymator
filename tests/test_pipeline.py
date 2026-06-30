from anonymator.ner import FakeNer
from anonymator.referential import Referential
from anonymator.pipeline import detect

def test_pipeline_combines_deterministic_and_ner():
    ref = Referential.load_default()
    ner = FakeNer({"Claire Martin": "PERSON"})
    text = "Claire Martin — mail c@x.fr"
    types = {e.type for e in detect(text, ner, ref)}
    assert {"PERSON", "EMAIL"} <= types

def test_pipeline_drops_inactive_types():
    ref = Referential.load_default()           # URL inactif par défaut
    ner = FakeNer({})
    out = detect("voir https://x.fr", ner, ref)
    assert all(e.type != "URL" for e in out)

def test_pipeline_deterministic_wins_overlap():
    ref = Referential.load_default()
    # le NER tente de tagger l'IBAN comme ORG : doit perdre
    iban = "FR7630006000011234567890189"
    ner = FakeNer({iban: "ORG"})
    out = detect(f"vir {iban}", ner, ref)
    assert any(e.type == "IBAN" for e in out)
    assert all(e.type != "ORG" for e in out)
