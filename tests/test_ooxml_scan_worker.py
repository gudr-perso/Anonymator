from anonymator.referential import Referential
from anonymator.ner import FakeNer
from anonymator.ui.model_loader import ModelLoader
from anonymator.ui.ooxml_scan_worker import OoxmlScanWorker, OoxmlScanResult
from tests.ooxml_fixtures import make_docx, make_pptx


def _run_worker(path, qtbot):
    loader = ModelLoader(FakeNer({"Claire Martin": "PERSON"}))
    worker = OoxmlScanWorker(path, loader, Referential.load_default())
    results = []
    worker.scan_finished.connect(results.append)
    with qtbot.waitSignal(worker.scan_finished, timeout=10000):
        worker.start()
    return results[0]


def test_worker_docx(tmp_path, qtbot):
    res = _run_worker(make_docx(tmp_path / "d.docx"), qtbot)
    assert isinstance(res, OoxmlScanResult)
    assert res.fmt == "docx"
    assert res.scanned  # au moins une unité avec entités
    assert res.units


def test_worker_pptx(tmp_path, qtbot):
    res = _run_worker(make_pptx(tmp_path / "p.pptx"), qtbot)
    assert res.fmt == "pptx"
    assert res.scanned
