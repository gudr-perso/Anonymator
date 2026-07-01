# tests/test_pdf_propagate.py
from anonymator.files.pdf.extract import PageText, WordBox
from anonymator.model import Entity
from anonymator.files.pdf import propagate


def _page(idx, words):
    """PageText jouet : offsets cohérents, rects factices."""
    boxes, parts, cursor = [], [], 0
    for i, w in enumerate(words):
        if i:
            parts.append(" "); cursor += 1
        start = cursor
        parts.append(w); cursor += len(w)
        boxes.append(WordBox(w, (0.0, 0.0, 1.0, 1.0), start, cursor))
    return PageText(idx, "".join(parts), boxes)


def _seed(page, i0, i1, etype, value):
    """Entité 'ner' couvrant les WordBox [i0, i1] de la page."""
    return Entity(etype, value, page.words[i0].char_start,
                  page.words[i1].char_end, "ner", 0.9, True)


def test_propagates_value_to_other_page():
    p0 = _page(0, ["Titulaire", "GUILLAUME", "DROGLAND"])
    p1 = _page(1, ["Client", "GUILLAUME", "DROGLAND", "ici"])
    ent = _seed(p0, 1, 2, "PERSON", "GUILLAUME DROGLAND")
    out = propagate.propagate_across_pages([p0, p1], [[ent], []])
    hits = [e for e in out[1]
            if e.type == "PERSON" and e.value == "GUILLAUME DROGLAND"]
    assert len(hits) == 1
    assert p1.text[hits[0].start:hits[0].end] == "GUILLAUME DROGLAND"
    assert hits[0].source == "propagated"


def test_numeric_only_value_not_propagated():
    p0 = _page(0, ["numero", "16"])
    p1 = _page(1, ["rue", "16", "bis"])
    ent = _seed(p0, 1, 1, "PERSON", "16")
    out = propagate.propagate_across_pages([p0, p1], [[ent], []])
    assert all(e.value != "16" for e in out[1])


def test_short_single_token_not_propagated():
    p0 = _page(0, ["particule", "Le"])
    p1 = _page(1, ["Le", "grand", "Le"])
    ent = _seed(p0, 1, 1, "PERSON", "Le")
    out = propagate.propagate_across_pages([p0, p1], [[ent], []])
    assert all(e.value != "Le" for e in out[1])


def test_matches_whole_words_only():
    p0 = _page(0, ["contact", "Martin"])
    p1 = _page(1, ["ecrit", "par", "Martinez"])
    ent = _seed(p0, 1, 1, "PERSON", "Martin")
    out = propagate.propagate_across_pages([p0, p1], [[ent], []])
    assert all(e.value != "Martin" for e in out[1])


def test_propagation_ignores_case_and_accents():
    p0 = _page(0, ["Client", "GUILLAUME"])
    p1 = _page(1, ["ref", "guillaume"])
    ent = _seed(p0, 1, 1, "PERSON", "GUILLAUME")
    out = propagate.propagate_across_pages([p0, p1], [[ent], []])
    assert any(e.value == "GUILLAUME" and e.source == "propagated"
               for e in out[1])


def test_unconfirmed_seed_not_propagated():
    p0 = _page(0, ["ref", "DUPONT"])
    p1 = _page(1, ["ici", "DUPONT"])
    ent = Entity("PERSON", "DUPONT", p0.words[1].char_start,
                 p0.words[1].char_end, "ner", 0.9, False)   # non confirmé
    out = propagate.propagate_across_pages([p0, p1], [[ent], []])
    assert all(e.value != "DUPONT" for e in out[1])
