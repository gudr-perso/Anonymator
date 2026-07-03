# tests/test_pdf_canvas.py
import pytest
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


def test_display_zoom_starts_at_one(qtbot):
    c = PdfCanvas(); qtbot.addWidget(c)
    assert c.display_zoom == pytest.approx(1.0)


def test_zoom_in_scales_view_up(qtbot):
    c = PdfCanvas(); qtbot.addWidget(c)
    c.zoom_in()
    assert c.display_zoom > 1.0
    assert c.transform().m11() == pytest.approx(c.display_zoom)
    assert c.transform().m22() == pytest.approx(c.display_zoom)


def test_zoom_out_scales_view_down(qtbot):
    c = PdfCanvas(); qtbot.addWidget(c)
    c.zoom_out()
    assert c.display_zoom < 1.0
    assert c.transform().m11() == pytest.approx(c.display_zoom)


def test_reset_zoom_returns_to_one(qtbot):
    c = PdfCanvas(); qtbot.addWidget(c)
    c.zoom_in(); c.zoom_in()
    c.reset_zoom()
    assert c.display_zoom == pytest.approx(1.0)
    assert c.transform().m11() == pytest.approx(1.0)


def test_zoom_in_clamped_to_max(qtbot):
    c = PdfCanvas(); qtbot.addWidget(c)
    for _ in range(60):
        c.zoom_in()
    assert c.display_zoom <= 8.0 + 1e-9


def test_zoom_out_clamped_to_min(qtbot):
    c = PdfCanvas(); qtbot.addWidget(c)
    for _ in range(60):
        c.zoom_out()
    assert c.display_zoom >= 0.25 - 1e-9


def test_clear_resets_display_zoom(qtbot):
    c = PdfCanvas(); qtbot.addWidget(c)
    c.zoom_in(); c.zoom_in()
    c.clear()
    assert c.display_zoom == pytest.approx(1.0)
    assert c.transform().m11() == pytest.approx(1.0)


def test_fit_to_width_with_no_page_keeps_zoom(qtbot):
    c = PdfCanvas(); qtbot.addWidget(c)
    c.fit_to_width()
    assert c.display_zoom == pytest.approx(1.0)


def test_fit_to_width_scales_page_to_viewport(qtbot, tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "du texte a afficher")
    png = pdf_io.render_page_at(src, 0)
    c = PdfCanvas(); qtbot.addWidget(c)
    c.resize(400, 600); c.show(); qtbot.waitExposed(c)
    c.set_page(png, zoom=2.0)
    c.fit_to_width()
    # la largeur de la page (échelle appliquée) remplit ~ la largeur visible
    scaled_w = c._scene.width() * c.display_zoom
    assert scaled_w <= c.viewport().width() + 1
    assert scaled_w >= c.viewport().width() - c.verticalScrollBar().sizeHint().width() - 6


def test_fit_to_width_sets_fit_mode(qtbot, tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "du texte a afficher")
    png = pdf_io.render_page_at(src, 0)
    c = PdfCanvas(); qtbot.addWidget(c)
    c.resize(400, 600); c.show(); qtbot.waitExposed(c)
    c.set_page(png, zoom=2.0)
    c.fit_to_width()
    assert c._fit_width is True


def test_manual_zoom_clears_fit_mode(qtbot, tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "du texte a afficher")
    png = pdf_io.render_page_at(src, 0)
    c = PdfCanvas(); qtbot.addWidget(c)
    c.resize(400, 600); c.show(); qtbot.waitExposed(c)
    c.set_page(png, zoom=2.0)
    c.fit_to_width()
    c.zoom_in()
    assert c._fit_width is False
