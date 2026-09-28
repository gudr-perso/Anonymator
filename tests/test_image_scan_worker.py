import threading

from PIL import Image

from anonymator.files.image.ocr import FakeOcr, OcrBox
from anonymator.ner import FakeNer
from anonymator.referential import Referential
from anonymator.ui.image_scan_worker import ImageScanWorker
from anonymator.ui.model_loader import ModelLoader


def _image(tmp_path):
    p = tmp_path / "capture.png"
    Image.new("RGB", (200, 100), (255, 255, 255)).save(p)
    return p


def _ocr():
    return FakeOcr([OcrBox("jean@exemple.fr", (0.0, 0.0, 120.0, 20.0), 0.9)])


def test_le_worker_emet_les_pages_analysees(qtbot, tmp_path):
    worker = ImageScanWorker(_image(tmp_path), _ocr, ModelLoader(FakeNer({})),
                             Referential.load_default())
    with qtbot.waitSignal(worker.scan_finished, timeout=10000) as blocker:
        worker.start()
    worker.wait()
    pages = blocker.args[0]
    assert len(pages) == 1
    assert [e.type for e in pages[0].entities] == ["EMAIL"]


def test_le_worker_emet_une_erreur_metier_lisible(qtbot, tmp_path):
    p = tmp_path / "photo.heic"
    p.write_bytes(b"pas une image")
    worker = ImageScanWorker(p, _ocr, ModelLoader(FakeNer({})),
                             Referential.load_default())
    with qtbot.waitSignal(worker.error, timeout=10000) as blocker:
        worker.start()
    worker.wait()
    assert "Format non supporté" in blocker.args[0]


def test_un_echec_de_chargement_du_moteur_ocr_remonte_a_l_ui(qtbot, tmp_path):
    """Construire RapidOcrEngine charge 32 Mo de modèles : un échec doit
    remonter via `error`, pas exploser en silence — c'est la leçon du bug
    « rien ne se passe » corrigé côté PDF."""
    def _boom():
        raise RuntimeError("modele OCR introuvable")

    worker = ImageScanWorker(_image(tmp_path), _boom, ModelLoader(FakeNer({})),
                             Referential.load_default())
    with qtbot.waitSignal(worker.error, timeout=10000) as blocker:
        worker.start()
    worker.wait()
    assert "modele OCR introuvable" in blocker.args[0]


def test_le_moteur_ocr_est_construit_dans_le_thread(qtbot, tmp_path):
    """Sinon l'interface gèle pendant le chargement des modèles — plusieurs
    secondes sur une photo."""
    fils = {}

    def _provider():
        fils["ocr"] = threading.get_ident()
        return _ocr()

    worker = ImageScanWorker(_image(tmp_path), _provider, ModelLoader(FakeNer({})),
                             Referential.load_default())
    assert "ocr" not in fils, "le moteur ne doit pas être construit à l'instanciation"
    with qtbot.waitSignal(worker.scan_finished, timeout=10000):
        worker.start()
    worker.wait()
    assert fils["ocr"] != threading.get_ident()
