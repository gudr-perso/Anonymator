# tests/test_pdf_review_session.py
from anonymator.referential import Referential
from anonymator.model import Entity
from anonymator.files.pdf.extract import WordBox
from anonymator.files.pdf.pdf_io import PageScan
from anonymator.core.pdf_review_session import PdfReviewSession


def _pagescan():
    words = [
        WordBox("Bonjour", (10, 10, 60, 20), 0, 7),
        WordBox("Claire", (62, 10, 100, 20), 8, 14),
        WordBox("Martin", (102, 10, 150, 20), 15, 21),
    ]
    ents = [Entity("PERSON", "Claire Martin", 8, 21, "ner")]
    return PageScan(0, "Bonjour Claire Martin", words, ents)


def _session():
    return PdfReviewSession([_pagescan()], Referential.load_default())


def test_types_and_values():
    s = _session()
    assert s.types() == ["PERSON"]
    assert s.values_for("PERSON") == [("Claire Martin", 1)]
    assert s.total_occurrences() == 1


def test_retained_rects_by_page_default():
    s = _session()
    rects = s.retained_rects_by_page()
    assert set(rects.keys()) == {0}
    assert (62, 10, 100, 20) in rects[0] and (102, 10, 150, 20) in rects[0]


def test_disabling_type_removes_rects():
    s = _session()
    s.set_type_enabled("PERSON", False)
    assert s.retained_rects_by_page().get(0, []) == []
    assert s.count_retained("PERSON") == 0


def test_disabling_value_removes_rects():
    s = _session()
    s.set_value_enabled("PERSON", "Claire Martin", False)
    assert s.retained_rects_by_page().get(0, []) == []


def test_unconfirmed_entity_starts_disabled():
    words = [WordBox("FR76", (10, 10, 40, 20), 0, 4)]
    ents = [Entity("IBAN", "FR76", 0, 4, "deterministic", confirmed=False)]
    s = PdfReviewSession([PageScan(0, "FR76", words, ents)],
                         Referential.load_default())
    assert s.is_value_enabled("IBAN", "FR76") is False
    assert s.retained_rects_by_page().get(0, []) == []


def test_manual_rects_added_to_retained():
    s = _session()
    s.add_manual_rect(0, (200, 200, 260, 230))
    rects = s.retained_rects_by_page()[0]
    assert (200, 200, 260, 230) in rects
    assert s.manual_rects(0) == [(200, 200, 260, 230)]


def test_clear_manual_rects():
    s = _session()
    s.add_manual_rect(0, (200, 200, 260, 230))
    s.clear_manual_rects(0)
    assert s.manual_rects(0) == []


def test_occurrence_exclusion():
    s = _session()
    s.set_occurrence_excluded(0, 0, True)
    assert s.retained_rects_by_page().get(0, []) == []


def test_report_lists_entities_and_manual_zones():
    s = _session()
    s.add_manual_rect(0, (200, 200, 260, 230))
    rows = s.report().to_rows()
    kinds = {r["type"] for r in rows}
    assert "PERSON" in kinds and "ZONE" in kinds


def test_retained_entity_rects_carries_type_for_overlay():
    s = _session()
    overlay = s.retained_entity_rects(0)
    assert all(len(item) == 2 for item in overlay)     # (rect, type)
    assert any(t == "PERSON" for _rect, t in overlay)
