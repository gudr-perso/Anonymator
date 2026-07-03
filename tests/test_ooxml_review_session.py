from dataclasses import dataclass
from anonymator.model import Entity
from anonymator.referential import Referential
from anonymator.files.ooxml.text_unit import TextUnit
from anonymator.core.ooxml_review_session import OoxmlReviewSession


@dataclass
class FakeRun:
    text: str


def _unit(loc, text):
    return TextUnit([FakeRun(text)], loc)


def _session(saved):
    units = [_unit("Corps", "Claire Martin et Marie Curie")]
    scanned = {0: [
        Entity("PERSON", "Claire Martin", 0, 13, "ner", 1.0, confirmed=True),
        Entity("PERSON", "Marie Curie", 17, 28, "ner", 1.0, confirmed=True),
    ]}

    def save_fn(out_path):
        saved["text"] = units[0].text()

    def post_fn(out_path, report):
        saved["report"] = report

    ref = Referential.load_default()
    return OoxmlReviewSession(units, scanned, ref, save_fn, post_fn), saved


def test_types_and_values():
    session, _ = _session({})
    assert session.types() == ["PERSON"]
    assert ("Claire Martin", 1) in session.values_for("PERSON")
    assert session.total_occurrences() == 2


def test_apply_masks_enabled_only():
    saved = {}
    session, saved = _session(saved)
    session.set_value_enabled("PERSON", "Marie Curie", False)
    session.apply_and_save("out.docx")
    assert saved["text"] == "[PERSONNE] et Marie Curie"


def test_disabling_type_keeps_all_clear():
    saved = {}
    session, saved = _session(saved)
    session.set_type_enabled("PERSON", False)
    session.apply_and_save("out.docx")
    assert saved["text"] == "Claire Martin et Marie Curie"


def test_is_value_confirmed_reflects_key_control():
    units = [_unit("Corps", "peu importe")]
    scanned = {0: [
        Entity("PERSON", "Claire Martin", 0, 13, "ner", 1.0, confirmed=True),
        Entity("IBAN", "FR76 XXX", 0, 8, "deterministic", 1.0, confirmed=False),
    ]}
    session = OoxmlReviewSession(units, scanned, Referential.load_default(),
                                 lambda out: None, lambda out, rep: None)
    assert session.is_value_confirmed("PERSON", "Claire Martin") is True
    assert session.is_value_confirmed("IBAN", "FR76 XXX") is False
    # non confirmé → décoché par défaut (opt-in)
    assert session.is_value_enabled("IBAN", "FR76 XXX") is False
