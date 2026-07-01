# tests/test_pdf_io.py
from datetime import datetime
import fitz
import pytest
from tests.pdf_fixtures import make_native_pdf, make_scanned_pdf
from anonymator.referential import Referential
from anonymator.ner import FakeNer
from anonymator.files.pdf import pdf_io
from anonymator.files.pdf.extract import ScannedPdfNotSupported


def _ref():
    return Referential.load_default()


def test_scan_pdf_returns_pagescan_with_entities(tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "Contact Claire Martin ici")
    pages = pdf_io.scan_pdf(src, FakeNer({"Claire Martin": "PERSON"}), _ref())
    assert len(pages) == 1
    ps = pages[0]
    assert ps.page_index == 0
    assert any(e.type == "PERSON" and e.value == "Claire Martin" for e in ps.entities)
    assert ps.words   # les boîtes sont conservées pour le mapping


def test_scan_pdf_rejects_scanned(tmp_path):
    src = make_scanned_pdf(tmp_path / "s.pdf")
    with pytest.raises(ScannedPdfNotSupported):
        pdf_io.scan_pdf(src, FakeNer({}), _ref())


def test_anonymize_pdf_text_writes_masked_txt(tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "Contact Claire Martin ici")
    res = pdf_io.anonymize_pdf_text(src, FakeNer({"Claire Martin": "PERSON"}),
                                    _ref(), tmp_path, datetime(2026, 1, 2, 3, 4, 5))
    assert res.output_path.suffix == ".txt"
    out = res.output_path.read_text(encoding="utf-8")
    assert "[PERSONNE]" in out and "Claire Martin" not in out


def test_anonymize_pdf_redact_destroys_and_saves(tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "Contact Claire Martin ici")
    pages = pdf_io.scan_pdf(src, FakeNer({"Claire Martin": "PERSON"}), _ref())
    ps = pages[0]
    from anonymator.files.pdf import mapping
    ent = next(e for e in ps.entities if e.value == "Claire Martin")
    rects = mapping.rects_for_entity(_page_text(ps), ent)
    out = pdf_io.anonymize_pdf_redact(src, {0: rects}, tmp_path,
                                      datetime(2026, 1, 2, 3, 4, 5))
    assert out.suffix == ".pdf"
    check = fitz.open(str(out))
    assert "Claire Martin" not in check[0].get_text()
    check.close()


def test_anonymize_pdf_text_from_session_honors_decochage(tmp_path):
    """Mode texte via la session : une valeur décochée reste en clair dans le .txt."""
    from anonymator.core.pdf_review_session import PdfReviewSession
    src = make_native_pdf(tmp_path / "n.pdf",
                          "Contact Claire Martin et Jean Dupont ici")
    pages = pdf_io.scan_pdf(
        src, FakeNer({"Claire Martin": "PERSON", "Jean Dupont": "PERSON"}), _ref())
    session = PdfReviewSession(pages, _ref())
    session.set_value_enabled("PERSON", "Jean Dupont", False)
    res = pdf_io.anonymize_pdf_text_from_session(
        src, session, tmp_path, datetime(2026, 1, 2, 3, 4, 5))
    assert res.output_path.suffix == ".txt"
    out = res.output_path.read_text(encoding="utf-8")
    assert "Jean Dupont" in out            # décoché → conservé en clair
    assert "Claire Martin" not in out      # coché → masqué
    assert "[PERSONNE]" in out
    # le rapport ne liste que l'entité réellement masquée
    originals = [r["original"] for r in res.report.to_rows()]
    assert "Claire Martin" in originals and "Jean Dupont" not in originals


def _page_text(ps):
    """Reconstruit un PageText à partir d'un PageScan pour appeler mapping."""
    from anonymator.files.pdf.extract import PageText
    return PageText(ps.page_index, ps.text, ps.words)


def test_render_page_at_returns_png(tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "un texte")
    png = pdf_io.render_page_at(src, 0)
    assert png[:4] == b"\x89PNG"
