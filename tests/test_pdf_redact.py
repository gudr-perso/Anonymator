# tests/test_pdf_redact.py
import fitz
from tests.pdf_fixtures import make_native_pdf
from anonymator.files.pdf import extract, mapping, redact
from anonymator.model import Entity


def test_redaction_really_destroys_text(tmp_path):
    """Test pivot : après rédaction, get_text() ne contient plus la valeur."""
    src = make_native_pdf(tmp_path / "n.pdf", "Contact Claire Martin fin")
    doc = extract.open_document(src)
    pt = extract.extract_page(doc[0], 0)
    ent = Entity("PERSON", "Claire Martin", pt.text.index("Claire"),
                 pt.text.index("Claire") + len("Claire Martin"), "ner")
    rects = mapping.rects_for_entity(pt, ent)
    redact.redact_page(doc[0], rects)
    out = tmp_path / "out.pdf"
    redact.save_redacted(doc, out)
    doc.close()

    check = fitz.open(str(out))
    assert "Claire Martin" not in check[0].get_text()
    assert "Contact" in check[0].get_text()   # le reste survit
    check.close()


def test_purge_metadata_clears_title_and_author(tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "du texte", title="Secret", author="Alice")
    doc = extract.open_document(src)
    redact.purge_metadata(doc)
    out = tmp_path / "out.pdf"
    redact.save_redacted(doc, out)
    doc.close()

    check = fitz.open(str(out))
    meta = check.metadata
    check.close()
    assert not meta.get("title") and not meta.get("author")
