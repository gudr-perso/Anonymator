from anonymator.files.textlayer import (
    WordBox, PageText, PageScan, rects_for_entity, rects_for_entities)
from anonymator.model import Entity


def _page():
    return PageText(0, "Jean Dupont paie", [
        WordBox("Jean", (0.0, 0.0, 10.0, 5.0), 0, 4),
        WordBox("Dupont", (11.0, 0.0, 25.0, 5.0), 5, 11),
        WordBox("paie", (26.0, 0.0, 34.0, 5.0), 12, 16),
    ])


def test_rects_for_entity_couvre_les_mots_recoupes():
    ent = Entity("PERSON", "Jean Dupont", 0, 11, "ner")
    assert rects_for_entity(_page(), ent) == [
        (0.0, 0.0, 10.0, 5.0), (11.0, 0.0, 25.0, 5.0)]


def test_rects_for_entities_dedoublonne():
    e1 = Entity("PERSON", "Jean", 0, 4, "ner")
    e2 = Entity("PERSON", "Jean", 0, 4, "ner")
    assert rects_for_entities(_page(), [e1, e2]) == [(0.0, 0.0, 10.0, 5.0)]


def test_textlayer_n_importe_pas_pymupdf():
    import anonymator.files.textlayer as m
    assert "fitz" not in getattr(m, "__dict__", {})


def test_page_scan_est_une_dataclass_pure():
    scan = PageScan(0, "abc", [], [])
    assert (scan.page_index, scan.text, scan.words, scan.entities) == (0, "abc", [], [])


def test_propagation_retrouve_une_valeur_confirmee_sur_une_autre_page():
    from anonymator.files.textlayer import propagate_across_pages
    p0 = PageText(0, "Jean Dupont", [
        WordBox("Jean", (0.0, 0.0, 10.0, 5.0), 0, 4),
        WordBox("Dupont", (11.0, 0.0, 25.0, 5.0), 5, 11),
    ])
    p1 = PageText(1, "vu Jean Dupont ici", [
        WordBox("vu", (0.0, 0.0, 4.0, 5.0), 0, 2),
        WordBox("Jean", (5.0, 0.0, 15.0, 5.0), 3, 7),
        WordBox("Dupont", (16.0, 0.0, 30.0, 5.0), 8, 14),
        WordBox("ici", (31.0, 0.0, 37.0, 5.0), 15, 18),
    ])
    confirmee = Entity("PERSON", "Jean Dupont", 0, 11, "ner")
    result = propagate_across_pages([p0, p1], [[confirmee], []])
    assert [e.value for e in result[1]] == ["Jean Dupont"]
