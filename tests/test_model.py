from anonymator.model import Entity


def test_entity_holds_span_and_metadata():
    e = Entity(type="EMAIL", value="a@b.fr", start=3, end=9,
               source="deterministic", confidence=1.0)
    assert e.type == "EMAIL"
    assert (e.start, e.end) == (3, 9)
    assert e.length == 6  # end - start


def test_entity_is_orderable_by_start_then_length():
    a = Entity("PERSON", "X", 0, 5, "ner", 0.9)
    b = Entity("PERSON", "Y", 0, 8, "ner", 0.9)
    assert sorted([b, a])[0] is a  # même start → plus court d'abord


def test_entity_confirmed_defaults_true():
    e = Entity("IBAN", "FR76...", 0, 5, "deterministic")
    assert e.confirmed is True


def test_entity_can_be_unconfirmed():
    e = Entity("IBAN", "FR00 0000", 0, 9, "deterministic", confidence=1.0, confirmed=False)
    assert e.confirmed is False
