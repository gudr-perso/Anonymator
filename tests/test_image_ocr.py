from PIL import Image
from anonymator.files.image.ocr import OcrBox, FakeOcr, NullOcr


def _img():
    return Image.new("RGB", (100, 50), (255, 255, 255))


def test_fake_ocr_rend_les_boites_fournies():
    boxes = [OcrBox("Jean", (0.0, 0.0, 10.0, 5.0), 0.9)]
    assert FakeOcr(boxes).read(_img()) == boxes


def test_null_ocr_ne_rend_rien():
    assert NullOcr().read(_img()) == []


def test_ocr_box_expose_un_rectangle_englobant():
    quad = [[10, 4], [30, 2], [31, 12], [11, 14]]
    box = OcrBox.from_quad("Dupont", quad, 0.8)
    assert box.rect == (10.0, 2.0, 31.0, 14.0)
    assert box.text == "Dupont"
