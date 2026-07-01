# tests/test_pdf_extract.py
import pytest
from tests.pdf_fixtures import make_native_pdf, make_scanned_pdf, make_encrypted_pdf
from anonymator.files.pdf import extract
from anonymator.files.pdf.extract import (
    ScannedPdfNotSupported, EncryptedPdfError, CorruptPdfError)


def test_open_native_pdf(tmp_path):
    p = make_native_pdf(tmp_path / "n.pdf", "Bonjour Claire Martin")
    doc = extract.open_document(p)
    assert doc.page_count == 1
    doc.close()


def test_open_encrypted_raises(tmp_path):
    p = make_encrypted_pdf(tmp_path / "e.pdf")
    with pytest.raises(EncryptedPdfError):
        extract.open_document(p)


def test_open_corrupt_raises(tmp_path):
    p = tmp_path / "bad.pdf"
    p.write_bytes(b"%PDF-1.4 this is not a real pdf")
    with pytest.raises(CorruptPdfError):
        extract.open_document(p)


def test_ensure_native_accepts_text_pdf(tmp_path):
    p = make_native_pdf(tmp_path / "n.pdf", "Un texte bien present ici")
    doc = extract.open_document(p)
    extract.ensure_native(doc)   # ne lève pas
    doc.close()


def test_ensure_native_rejects_scanned(tmp_path):
    p = make_scanned_pdf(tmp_path / "s.pdf")
    doc = extract.open_document(p)
    with pytest.raises(ScannedPdfNotSupported):
        extract.ensure_native(doc)
    doc.close()


def test_extract_page_flat_text_and_boxes(tmp_path):
    p = make_native_pdf(tmp_path / "n.pdf", "Bonjour Claire Martin")
    doc = extract.open_document(p)
    pt = extract.extract_page(doc[0], 0)
    doc.close()
    assert "Claire" in pt.text and "Martin" in pt.text
    assert pt.words, "au moins un mot"
    w = pt.words[0]
    assert pt.text[w.char_start:w.char_end] == w.text
    x0, y0, x1, y1 = w.rect
    assert x1 > x0 and y1 > y0


def test_extract_pages_returns_one_per_page(tmp_path):
    p = make_native_pdf(tmp_path / "n.pdf", "Page unique de test")
    doc = extract.open_document(p)
    pages = extract.extract_pages(doc)
    doc.close()
    assert len(pages) == 1
    assert pages[0].page_index == 0
