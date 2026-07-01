# tests/test_pdf_fixtures.py
import fitz
from tests.pdf_fixtures import make_native_pdf, make_scanned_pdf, make_encrypted_pdf


def test_native_pdf_has_extractable_text(tmp_path):
    p = tmp_path / "n.pdf"
    make_native_pdf(p, "Contact Claire Martin ici")
    doc = fitz.open(str(p))
    assert "Claire Martin" in doc[0].get_text()
    doc.close()


def test_scanned_pdf_has_no_text(tmp_path):
    p = tmp_path / "s.pdf"
    make_scanned_pdf(p)
    doc = fitz.open(str(p))
    assert doc[0].get_text().strip() == ""
    doc.close()


def test_encrypted_pdf_needs_pass(tmp_path):
    p = tmp_path / "e.pdf"
    make_encrypted_pdf(p, "secret")
    doc = fitz.open(str(p))
    assert doc.needs_pass  # returns 1 (int) in PyMuPDF 1.28, truthy == needs password
    doc.close()
