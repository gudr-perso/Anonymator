# tests/test_pdf_render.py
from tests.pdf_fixtures import make_native_pdf
from anonymator.files.pdf import extract, render


def test_render_page_returns_png_bytes(tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "un texte a rendre")
    doc = extract.open_document(src)
    png = render.render_page(doc[0])
    doc.close()
    assert png[:8] == b"\x89PNG\r\n\x1a\n"   # signature PNG
    assert len(png) > 100


def test_render_zoom_increases_size(tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "un texte a rendre")
    doc = extract.open_document(src)
    small = render.render_page(doc[0], zoom=1.0)
    big = render.render_page(doc[0], zoom=3.0)
    doc.close()
    assert len(big) > len(small)
