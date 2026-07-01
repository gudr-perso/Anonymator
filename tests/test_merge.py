from anonymator.model import Entity
from anonymator.merge import merge_entities

def test_no_overlap_keeps_all():
    a = Entity("EMAIL", "a@b.fr", 0, 6, "deterministic", 1.0)
    b = Entity("PERSON", "Zoé", 10, 13, "ner", 0.9)
    assert sorted(merge_entities([a, b])) == sorted([a, b])

def test_deterministic_wins_over_ner_on_overlap():
    det = Entity("IBAN", "FR76...", 5, 30, "deterministic", 1.0)
    ner = Entity("ORG", "FR76 3000", 5, 14, "ner", 0.95)
    assert merge_entities([ner, det]) == [det]

def test_longer_ner_span_wins_over_shorter_when_same_source():
    short = Entity("PERSON", "Martin", 0, 6, "ner", 0.8)
    long = Entity("PERSON", "Martin Dupont", 0, 13, "ner", 0.8)
    assert merge_entities([short, long]) == [long]

def test_longer_deterministic_iban_beats_contained_phone():
    # cas réel : la regex téléphone matche un sous-bloc à l'intérieur d'un IBAN avec espaces.
    # Les deux sont déterministes ; l'IBAN (plus long) doit gagner, le téléphone contenu disparaît.
    iban = Entity("IBAN", "FR76 3000 6000 0112 3456 7890 189", 5, 38, "deterministic", 1.0)
    phone = Entity("PHONE", "0112 3456 78", 20, 32, "deterministic", 1.0)
    assert merge_entities([phone, iban]) == [iban]

def test_forced_rule_wins_over_ner_overlap():
    # une entité forcée (source="rule") doit survivre face à un NER chevauchant
    forced = Entity("REGLE_INTERNE", "PRJ-2024", 0, 8, "rule", 1.0)
    ner = Entity("ORG", "PRJ-2024", 0, 8, "ner", 0.95)
    kept = merge_entities([ner, forced])
    assert len(kept) == 1
    assert kept[0].source == "rule"
