# tests/test_pdf_mapping.py
from anonymator.model import Entity
from anonymator.files.pdf.extract import WordBox, PageText
from anonymator.files.pdf import mapping


def _page():
    # texte plat : "Bonjour Claire Martin"  (offsets 0..21)
    #               0......7......14
    return PageText(0, "Bonjour Claire Martin", [
        WordBox("Bonjour", (10, 10, 60, 20), 0, 7),
        WordBox("Claire", (62, 10, 100, 20), 8, 14),
        WordBox("Martin", (102, 10, 150, 20), 15, 21),
    ])


def test_single_word_entity_maps_to_its_rect():
    pt = _page()
    ent = Entity("PERSON", "Claire", 8, 14, "ner")
    rects = mapping.rects_for_entity(pt, ent)
    assert rects == [(62, 10, 100, 20)]


def test_multi_word_entity_maps_to_all_intersecting_rects():
    pt = _page()
    ent = Entity("PERSON", "Claire Martin", 8, 21, "ner")
    rects = mapping.rects_for_entity(pt, ent)
    assert (62, 10, 100, 20) in rects and (102, 10, 150, 20) in rects
    assert len(rects) == 2


def test_partial_overlap_still_selects_word():
    pt = _page()
    # entité couvrant "laire" (déborde à l'intérieur du mot Claire)
    ent = Entity("X", "laire", 9, 14, "ner")
    rects = mapping.rects_for_entity(pt, ent)
    assert rects == [(62, 10, 100, 20)]


def test_unmappable_entity_returns_empty():
    pt = _page()
    ent = Entity("X", "zzz", 100, 103, "ner")   # hors de tout mot
    assert mapping.rects_for_entity(pt, ent) == []


def test_rects_for_entities_aggregates():
    pt = _page()
    ents = [Entity("PERSON", "Bonjour", 0, 7, "ner"),
            Entity("PERSON", "Martin", 15, 21, "ner")]
    rects = mapping.rects_for_entities(pt, ents)
    assert (10, 10, 60, 20) in rects and (102, 10, 150, 20) in rects
