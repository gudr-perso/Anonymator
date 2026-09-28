from datetime import datetime

from PIL import Image

from anonymator.files.image import image_io
from anonymator.files.image.ocr import FakeOcr, OcrBox
from anonymator.ner import FakeNer
from anonymator.referential import Referential


def _image(tmp_path):
    p = tmp_path / "capture.png"
    Image.new("RGB", (200, 100), (255, 255, 255)).save(p)
    return p


def _ocr():
    return FakeOcr([
        OcrBox("Contact", (0.0, 0.0, 50.0, 20.0), 0.9),
        OcrBox("jean@exemple.fr", (55.0, 0.0, 180.0, 20.0), 0.9),
    ])


def test_scan_image_rend_une_page_unique_avec_ses_entites(tmp_path):
    pages = image_io.scan_image(_image(tmp_path), _ocr(), FakeNer({}),
                                Referential.load_default())
    assert len(pages) == 1
    page = pages[0]
    assert page.page_index == 0
    assert page.text == "Contact jean@exemple.fr"
    assert [e.type for e in page.entities] == ["EMAIL"]


def test_les_rectangles_de_l_entite_pointent_sur_la_bonne_boite(tmp_path):
    from anonymator.files.textlayer import PageText, rects_for_entity
    page = image_io.scan_image(_image(tmp_path), _ocr(), FakeNer({}),
                               Referential.load_default())[0]
    pt = PageText(0, page.text, page.words)
    assert rects_for_entity(pt, page.entities[0]) == [(55.0, 0.0, 180.0, 20.0)]


def test_anonymize_image_redact_ecrit_un_fichier_horodate(tmp_path):
    src = _image(tmp_path)
    out_dir = tmp_path / "sortie"
    out = image_io.anonymize_image_redact(
        src, [(0.0, 0.0, 50.0, 20.0)], out_dir, datetime(2026, 9, 23, 14, 30, 0))
    assert out.name == "capture_ano_20260923143000.png"
    assert out.parent == out_dir


def test_le_fichier_de_sortie_a_bien_ses_pixels_detruits(tmp_path):
    src = _image(tmp_path)
    out = image_io.anonymize_image_redact(
        src, [(10.0, 10.0, 40.0, 40.0)], tmp_path / "s", datetime(2026, 9, 23))
    assert Image.open(out).crop((10, 10, 40, 40)).getextrema() == (
        (0, 0), (0, 0), (0, 0))


def test_l_original_n_est_jamais_modifie(tmp_path):
    src = _image(tmp_path)
    avant = src.read_bytes()
    image_io.anonymize_image_redact(
        src, [(0.0, 0.0, 200.0, 100.0)], tmp_path / "s", datetime(2026, 9, 23))
    assert src.read_bytes() == avant
