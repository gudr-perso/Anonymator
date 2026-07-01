# tests/test_file_anonymize_worker.py
from datetime import datetime
from anonymator.referential import Referential
from anonymator.ner import FakeNer
from anonymator.ui.model_loader import ModelLoader
from anonymator.ui.file_anonymize_worker import FileAnonymizeWorker

WHEN = datetime(2026, 1, 2, 3, 4, 5)


def _csv(tmp_path):
    src = tmp_path / "f.csv"
    src.write_bytes("Nom;Montant\nClaire Martin;100,00\n".encode("cp1252"))
    return src


def test_anonymize_worker_writes_output(qtbot, tmp_path):
    src = _csv(tmp_path)
    worker = FileAnonymizeWorker(src, ModelLoader(FakeNer({"Claire Martin": "PERSON"})),
                                 Referential.load_default(), tmp_path, WHEN)
    with qtbot.waitSignal(worker.done, timeout=5000) as blocker:
        worker.start()
    worker.wait()
    result = blocker.args[0]
    assert result.output_path.exists()
    out = result.output_path.read_bytes().decode("cp1252")
    assert "[PERSONNE]" in out and "Claire Martin" not in out


def test_anonymize_worker_error_on_detector_load(qtbot, tmp_path):
    """La construction du détecteur se fait DANS le thread : un échec remonte
    via `error` au lieu d'exploser en silence sur le thread principal."""
    src = _csv(tmp_path)

    class BoomLoader:
        def get(self):
            raise RuntimeError("échec chargement modèle")

    worker = FileAnonymizeWorker(src, BoomLoader(), Referential.load_default(),
                                 tmp_path, WHEN)
    with qtbot.waitSignal(worker.error, timeout=5000) as blocker:
        worker.start()
    worker.wait()
    assert "échec chargement modèle" in blocker.args[0]


def test_anonymize_worker_error_on_unsupported_format(qtbot, tmp_path):
    src = tmp_path / "f.docx"
    src.write_bytes(b"stub")
    worker = FileAnonymizeWorker(src, ModelLoader(FakeNer({})),
                                 Referential.load_default(), tmp_path, WHEN)
    with qtbot.waitSignal(worker.error, timeout=5000):
        worker.start()
    worker.wait()
