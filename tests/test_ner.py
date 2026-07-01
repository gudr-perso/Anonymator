from anonymator.model import Entity
from anonymator.ner import FakeNer, NullNer


def test_fake_ner_returns_configured_entities():
    ner = FakeNer({"Claire Martin": "PERSON"})
    text = "Bonjour Claire Martin."
    out = ner.detect(text, labels=["PERSON"])
    assert out == [Entity("PERSON", "Claire Martin", 8, 21, "ner", 1.0)]


def test_fake_ner_finds_all_occurrences():
    ner = FakeNer({"Zoé": "PERSON"})
    out = ner.detect("Zoé et Zoé", labels=["PERSON"])
    assert [(e.start, e.end) for e in out] == [(0, 3), (7, 10)]


def test_nullner_returns_empty():
    assert NullNer().detect("Jean habite à Toulouse", ["personne", "adresse postale"]) == []


def test_nullner_satisfies_protocol():
    from anonymator.ner import NerDetector
    det: NerDetector = NullNer()
    assert det.detect("x", []) == []
