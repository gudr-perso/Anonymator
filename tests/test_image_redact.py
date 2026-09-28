from PIL import Image
from anonymator.files.image.redact import redact_image


def test_la_zone_caviardee_est_uniforme():
    img = Image.new("RGB", (100, 50), (255, 255, 255))
    img.putpixel((20, 20), (255, 0, 0))     # un pixel à détruire
    out = redact_image(img, [(10.0, 10.0, 40.0, 40.0)])
    zone = out.crop((10, 10, 40, 40))
    assert zone.getextrema() == ((0, 0), (0, 0), (0, 0))


def test_le_reste_de_l_image_est_intact():
    img = Image.new("RGB", (100, 50), (255, 255, 255))
    out = redact_image(img, [(10.0, 10.0, 40.0, 40.0)])
    assert out.getpixel((80, 25)) == (255, 255, 255)


def test_l_image_source_n_est_pas_modifiee():
    img = Image.new("RGB", (100, 50), (255, 255, 255))
    redact_image(img, [(10.0, 10.0, 40.0, 40.0)])
    assert img.getpixel((20, 20)) == (255, 255, 255)


def test_un_rectangle_deborde_est_ramene_dans_l_image():
    img = Image.new("RGB", (100, 50), (255, 255, 255))
    out = redact_image(img, [(-20.0, -20.0, 500.0, 500.0)])
    assert out.getextrema() == ((0, 0), (0, 0), (0, 0))


def test_aucun_rectangle_rend_une_copie_identique():
    img = Image.new("RGB", (10, 10), (7, 8, 9))
    # tobytes() et non getdata() : ce dernier est deprecie (retrait Pillow 14).
    assert redact_image(img, []).tobytes() == img.tobytes()
