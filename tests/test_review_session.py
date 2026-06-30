from anonymator.model import Entity
from anonymator.referential import Referential
from anonymator.core.review_session import ReviewSession

REF = Referential.load_default()

def _session():
    text = "Claire Martin, mail c@x.fr, société SARL Bidule"
    ents = [Entity("PERSON", "Claire Martin", 0, 13, "ner", 0.9),
            Entity("EMAIL", "c@x.fr", 20, 26, "deterministic", 1.0),
            Entity("ORG", "SARL Bidule", 36, 47, "ner", 0.8)]
    return ReviewSession(text, ents)

def test_all_detected_retained_by_default():
    s = _session()
    assert {e.type for e in s.retained()} == {"PERSON", "EMAIL", "ORG"}
    assert s.masked_text(REF) == "[PERSONNE], mail [EMAIL], société [ORG]"

def test_disable_single_entity():
    s = _session()
    s.set_entity_enabled(2, False)            # l'ORG
    assert "SARL Bidule" in s.masked_text(REF)
    assert all(e.type != "ORG" for e in s.retained())

def test_disable_whole_type():
    s = _session()
    s.set_type_enabled("PERSON", False)
    assert s.masked_text(REF).startswith("Claire Martin")

def test_add_manual_entity():
    s = _session()
    s.add_manual("PERSON", 0, 13)             # idempotent sur un span déjà là
    assert s.masked_text(REF).count("[PERSONNE]") == 1

def test_report_counts_retained_only():
    s = _session()
    s.set_type_enabled("ORG", False)
    rows = s.report(REF).to_rows()
    assert {r["type"] for r in rows} == {"PERSON", "EMAIL"}
