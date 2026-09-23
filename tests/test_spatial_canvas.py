from anonymator.ui.spatial_canvas import SpatialCanvas, scene_rect_to_source


def test_conversion_de_coordonnees_a_zoom_1():
    assert scene_rect_to_source(10.0, 20.0, 30.0, 40.0, 1.0) == (10.0, 20.0, 30.0, 40.0)


def test_conversion_normalise_l_ordre_des_coins():
    assert scene_rect_to_source(30.0, 40.0, 10.0, 20.0, 1.0) == (10.0, 20.0, 30.0, 40.0)


def test_pdf_canvas_reste_un_alias():
    from anonymator.ui.pdf_canvas import PdfCanvas
    assert PdfCanvas is SpatialCanvas
