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


def test_pipeline_detects_secrets():
    ref = Referential.load_default()
    ner = FakeNer({})
    ents = detect("mot de passe : V3lo!2026#Claire", ner, ref)
    assert any(e.type == "PASSWORD" for e in ents)


def test_pipeline_filters_stoplist():
    ref = Referential.load_default()
    ner = FakeNer({"service client": "ORG", "Claire Martin": "PERSON"})
    ents = detect("appel au service client par Claire Martin", ner, ref)
    types_values = {(e.type, e.value) for e in ents}
    assert ("ORG", "service client") not in types_values
    assert ("PERSON", "Claire Martin") in types_values


from anonymator.user_rules import UserRules, Rule


def test_pipeline_forces_mask_rule():
    ref = Referential.load_default().with_user_rules(
        UserRules([Rule("simple", "PRJ-####", "mask", True, "projet")]))
    ner = FakeNer({})
    ents = detect("dossier PRJ-2024", ner, ref)
    assert any(e.type == "REGLE_INTERNE" and e.value == "PRJ-2024" for e in ents)


def test_pipeline_keep_rule_shields_detection():
    # une valeur qu'un détecteur aurait masquée est conservée grâce à keep
    ref = Referential.load_default().with_user_rules(
        UserRules([Rule("simple", "A#######", "keep", True, "codes")]))
    ner = FakeNer({"A0000015": "ADDRESS"})
    ents = detect("code A0000015", ner, ref)
    assert all(e.value != "A0000015" for e in ents)
