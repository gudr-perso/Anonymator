# tests/test_pdf_canvas.py
from tests.pdf_fixtures import make_native_pdf
from anonymator.files.pdf import pdf_io
from anonymator.ui.pdf_canvas import PdfCanvas, scene_rect_to_points


def test_scene_to_points_divides_by_zoom_and_orders():
    # scène (20,40)->(60,80) à zoom 2 → points (10,20)->(30,40)
    assert scene_rect_to_points(60, 80, 20, 40, 2.0) == (10.0, 20.0, 30.0, 40.0)


def test_set_page_loads_pixmap(qtbot, tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "du texte a afficher")
    png = pdf_io.render_page_at(src, 0)
    c = PdfCanvas(); qtbot.addWidget(c)
    c.set_page(png, zoom=2.0)
    assert c.has_page() is True


def test_set_overlays_draws_items(qtbot, tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "du texte a afficher")
    png = pdf_io.render_page_at(src, 0)
    c = PdfCanvas(); qtbot.addWidget(c)
    c.set_page(png, zoom=2.0)
    c.set_overlays([((10, 10, 50, 20), "PERSON")], [(60, 60, 90, 80)])
    assert c.overlay_count() == 2   # 1 entité + 1 zone manuelle


def test_draw_mode_emits_points(qtbot, tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "du texte a afficher")
    png = pdf_io.render_page_at(src, 0)
    c = PdfCanvas(); qtbot.addWidget(c)
    c.set_page(png, zoom=2.0)
    c.set_draw_mode(True)
    captured = {}
    c.manual_rect_drawn.connect(lambda r: captured.setdefault("r", r))
    c._finish_manual((20, 40), (60, 80))   # helper interne : coords scène
    assert captured["r"] == (10.0, 20.0, 30.0, 40.0)
