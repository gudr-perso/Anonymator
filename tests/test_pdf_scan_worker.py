# tests/test_pdf_scan_worker.py
from tests.pdf_fixtures import make_native_pdf, make_scanned_pdf
from anonymator.referential import Referential
from anonymator.ner import FakeNer
from anonymator.ui.model_loader import ModelLoader
from anonymator.ui.pdf_scan_worker import PdfScanWorker


def test_scan_worker_emits_pages(qtbot, tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "Contact Claire Martin ici")
    worker = PdfScanWorker(src, ModelLoader(FakeNer({"Claire Martin": "PERSON"})),
                           Referential.load_default())
    with qtbot.waitSignal(worker.scan_finished, timeout=5000) as blocker:
        worker.start()
    worker.wait()
    pages = blocker.args[0]
    assert pages and pages[0].entities


def test_scan_worker_emits_error_on_scanned(qtbot, tmp_path):
    src = make_scanned_pdf(tmp_path / "s.pdf")
    worker = PdfScanWorker(src, ModelLoader(FakeNer({})), Referential.load_default())
    with qtbot.waitSignal(worker.error, timeout=5000) as blocker:
        worker.start()
    worker.wait()
    assert "OCR" in blocker.args[0] or "scann" in blocker.args[0].lower()


def test_scan_worker_emits_error_when_detector_load_fails(qtbot, tmp_path):
    """Le détecteur est construit DANS le thread : un échec de chargement du
    modèle est capté et remonté via `error`, pas laissé exploser en silence
    sur le thread principal (cause du bug « rien ne se passe » dans l'exe)."""
    src = make_native_pdf(tmp_path / "n.pdf", "Contact Claire Martin ici")

    class BoomLoader:
        def get(self):
            raise RuntimeError("échec chargement modèle")

    worker = PdfScanWorker(src, BoomLoader(), Referential.load_default())
    with qtbot.waitSignal(worker.error, timeout=5000) as blocker:
        worker.start()
    worker.wait()
    assert "échec chargement modèle" in blocker.args[0]
