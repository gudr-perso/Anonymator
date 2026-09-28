import pytest
from PIL import Image

from anonymator.files.image import ocr as ocr_mod


class _FausseSortie:
    boxes = [[[10, 4], [30, 2], [31, 12], [11, 14]]]
    txts = ("Dupont",)
    scores = (0.87,)


class _FauxMoteur:
    def __init__(self, *a, **k):
        self.params = k.get("params")

    def __call__(self, arr):
        return _FausseSortie()


def test_l_adaptateur_convertit_les_quadrilateres_en_rectangles(monkeypatch):
    monkeypatch.setattr(ocr_mod, "_load_rapidocr", lambda: _FauxMoteur)
    engine = ocr_mod.RapidOcrEngine()
    boxes = engine.read(Image.new("RGB", (50, 20), (255, 255, 255)))
    assert len(boxes) == 1
    assert boxes[0].text == "Dupont"
    assert boxes[0].rect == (10.0, 2.0, 31.0, 14.0)
    assert boxes[0].confidence == pytest.approx(0.87)


def test_une_sortie_vide_ne_casse_rien(monkeypatch):
    class _Vide:
        boxes = None
        txts = None
        scores = None

    class _Moteur(_FauxMoteur):
        def __call__(self, arr):
            return _Vide()

    monkeypatch.setattr(ocr_mod, "_load_rapidocr", lambda: _Moteur)
    assert ocr_mod.RapidOcrEngine().read(
        Image.new("RGB", (10, 10), (0, 0, 0))) == []


def test_une_grande_image_est_reduite_mais_les_boites_reviennent_a_l_echelle(
        monkeypatch):
    """Une image de 8000 px est réduite avant l'OCR : les coordonnées rendues
    doivent être celles de l'IMAGE D'ORIGINE, sinon le caviardage tombe à côté."""
    vues = {}

    class _Moteur(_FauxMoteur):
        def __call__(self, arr):
            vues["taille"] = (arr.shape[1], arr.shape[0])
            return _FausseSortie()

    monkeypatch.setattr(ocr_mod, "_load_rapidocr", lambda: _Moteur)
    engine = ocr_mod.RapidOcrEngine()
    boxes = engine.read(Image.new("RGB", (8000, 4000), (255, 255, 255)))
    facteur = 8000 / ocr_mod.MAX_SIDE
    assert vues["taille"] == (ocr_mod.MAX_SIDE, ocr_mod.MAX_SIDE // 2)
    # La boîte fictive (10,2)-(31,14) doit être remise à l'échelle d'origine.
    assert boxes[0].rect == pytest.approx(
        (10 * facteur, 2 * facteur, 31 * facteur, 14 * facteur))


def test_une_petite_image_n_est_pas_redimensionnee(monkeypatch):
    vues = {}

    class _Moteur(_FauxMoteur):
        def __call__(self, arr):
            vues["taille"] = (arr.shape[1], arr.shape[0])
            return _FausseSortie()

    monkeypatch.setattr(ocr_mod, "_load_rapidocr", lambda: _Moteur)
    boxes = ocr_mod.RapidOcrEngine().read(Image.new("RGB", (50, 20), (0, 0, 0)))
    assert vues["taille"] == (50, 20)
    assert boxes[0].rect == (10.0, 2.0, 31.0, 14.0)


def test_les_modeles_sont_verrouilles_sur_les_fichiers_embarques(monkeypatch):
    captured = {}

    class _Moteur(_FauxMoteur):
        def __init__(self, *a, **k):
            captured.update(k.get("params") or {})

    monkeypatch.setattr(ocr_mod, "_load_rapidocr", lambda: _Moteur)
    ocr_mod.RapidOcrEngine()
    for key in ("Det.model_path", "Rec.model_path", "Cls.model_path"):
        assert key in captured, f"{key} doit etre impose"
        assert str(captured[key]).endswith(".onnx")
