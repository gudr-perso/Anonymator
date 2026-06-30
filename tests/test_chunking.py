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
    text = ("x " * 40) + "Claire Martin"      # le nom est loin dans le texte
    ents = detect_long(text, ner, ref, max_len=50)
    person = next(e for e in ents if e.type == "PERSON")
    assert text[person.start:person.end] == "Claire Martin"
