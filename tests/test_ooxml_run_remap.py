from dataclasses import dataclass
from anonymator.model import Entity
from anonymator.referential import Referential
from anonymator.files.ooxml import run_remap


@dataclass
class FakeRun:
    text: str


def _ref():
    return Referential.load_default()


def _runs(*texts):
    return [FakeRun(t) for t in texts]


def _ent(value, start, end, etype="PERSON"):
    return Entity(etype, value, start, end, "ner", 1.0)


def test_build_offsets_concatenates_and_maps():
    runs = _runs("Contact : ", "Jean ", "Dup", "ont")
    text, spans = run_remap.build_offsets(runs)
    assert text == "Contact : Jean Dupont"
    assert spans == [(0, 0, 10), (1, 10, 15), (2, 15, 18), (3, 18, 21)]


def test_span_within_single_run():
    runs = _runs("Bonjour Jean Dupont !")
    run_remap.apply(runs, [_ent("Jean Dupont", 8, 19)], _ref())
    assert runs[0].text == "Bonjour [PERSONNE] !"


def test_span_across_three_runs_preserves_untouched_runs():
    runs = _runs("Contact : ", "Jean ", "Dup", "ont", " (svc)")
    run_remap.apply(runs, [_ent("Jean Dupont", 10, 21)], _ref())
    assert runs[0].text == "Contact : "
    assert runs[1].text == "[PERSONNE]"
    assert runs[2].text == ""
    assert runs[3].text == ""
    assert runs[4].text == " (svc)"
    assert "".join(r.text for r in runs) == "Contact : [PERSONNE] (svc)"


def test_empty_runs_interspersed():
    runs = _runs("Jean", "", " ", "Dupont")
    run_remap.apply(runs, [_ent("Jean Dupont", 0, 11)], _ref())
    assert "".join(r.text for r in runs) == "[PERSONNE]"


def test_two_entities_same_paragraph():
    runs = _runs("De Jean Dupont a Marie Curie")
    ents = [_ent("Jean Dupont", 3, 14), _ent("Marie Curie", 17, 28)]
    run_remap.apply(runs, ents, _ref())
    assert runs[0].text == "De [PERSONNE] a [PERSONNE]"


def test_entity_at_start_and_end():
    runs = _runs("Jean Dupont")
    run_remap.apply(runs, [_ent("Jean Dupont", 0, 11)], _ref())
    assert runs[0].text == "[PERSONNE]"


def test_zero_width_span_is_ignored():
    runs = _runs("Hello")
    run_remap.apply(runs, [_ent("", 2, 2)], _ref())
    assert runs[0].text == "Hello"
