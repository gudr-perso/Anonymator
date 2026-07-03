from anonymator.referential import Referential
from anonymator.ner import FakeNer
from anonymator.core.chunking import chunk_spans, detect_long

def test_chunk_spans_cover_text_without_overlap():
    text = "abc def ghi jkl mno pqr"
    spans = chunk_spans(text, max_len=10)
    assert spans[0][0] == 0
    assert spans[-1][1] == len(text)
    for (s, e) in spans:
        assert e - s <= 10 or " " not in text[s:e]  # ne coupe pas en plein mot

def test_detect_long_rebases_offsets():
    ref = Referential.load_default()
    ner = FakeNer({"Claire Martin": "PERSON"})
    # "x " * 14 = 28 chars, puis "Claire Martin" débute au char 28 — tient
    # entier dans le 2ème chunk (max_len=30), ce qui teste le rebase d'offset
    text = ("x " * 14) + "Claire Martin"
    ents = detect_long(text, ner, ref, max_len=30)
    person = next(e for e in ents if e.type == "PERSON")
    assert text[person.start:person.end] == "Claire Martin"


def test_detect_long_does_not_split_deterministic_entity():
    # Le découpage sert à contourner la troncature GLiNER (NER). Il ne doit PAS
    # scinder une entité déterministe (IBAN, tél…) qui contient des espaces et
    # chevauche une frontière de chunk. Régression : IBAN coupé en deux.
    ref = Referential.load_default()
    ner = FakeNer({})
    iban = "FR76 3000 4000 1200 0000 1234 567"
    text = ("mot " * 10) + iban + " fin"   # frontière de chunk au milieu de l'IBAN
    ents = detect_long(text, ner, ref, max_len=55)
    ibans = [e.value for e in ents if e.type == "IBAN"]
    assert iban in ibans, ibans
