from anonymator.core.spatial_review_session import SpatialReviewSession
from anonymator.files.textlayer import PageScan, WordBox
from anonymator.model import Entity
from anonymator.referential import Referential


def test_session_accepte_une_page_unique():
    page = PageScan(0, "Jean Dupont", [
        WordBox("Jean", (0.0, 0.0, 10.0, 5.0), 0, 4),
        WordBox("Dupont", (11.0, 0.0, 25.0, 5.0), 5, 11),
    ], [Entity("PERSON", "Jean Dupont", 0, 11, "ner")])
    s = SpatialReviewSession([page], Referential.load_default())
    assert s.types() == ["PERSON"]
    assert len(s.retained_rects_by_page()[0]) == 2


def test_pdf_review_session_reste_un_alias():
    from anonymator.core.pdf_review_session import PdfReviewSession
    assert PdfReviewSession is SpatialReviewSession
