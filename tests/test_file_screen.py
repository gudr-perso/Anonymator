from datetime import datetime
from anonymator.referential import Referential
from anonymator.ner import FakeNer
from anonymator.ui.model_loader import ModelLoader
from anonymator.ui.preferences import Preferences
from anonymator.ui.file_screen import FileScreen
from anonymator.ui.file_scan_worker import FileScanWorker
from anonymator.files import csv_io
from anonymator.files.columns import default_maskable_columns


def test_scan_worker_emits_result(qtbot, tmp_path):
    src = tmp_path / "f.csv"
    src.write_bytes("Nom;Montant\nClaire Martin;100,00\n".encode("cp1252"))
    doc = csv_io.read_csv(src)
    cols = default_maskable_columns(doc.rows, doc.has_header)
    worker = FileScanWorker(doc, FakeNer({"Claire Martin": "PERSON"}),
                            Referential.load_default(), cols)
    with qtbot.waitSignal(worker.scan_finished, timeout=5000) as blocker:
        worker.start()
    worker.wait()           # ensure thread finishes before teardown
    scanned = blocker.args[0]
    assert (1, 0) in scanned


def test_run_on_csv_writes_output(qtbot, tmp_path):
    src = tmp_path / "f.csv"
    src.write_bytes("Nom;Montant\nClaire Martin;100,00\n".encode("cp1252"))
    prefs = Preferences(output_dir=str(tmp_path))
    loader = ModelLoader(FakeNer({"Claire Martin": "PERSON"}))
    screen = FileScreen(Referential.load_default(), loader, prefs, on_back=lambda: None)
    qtbot.addWidget(screen)
    screen.load_path(str(src))
    result = screen.run(when=datetime(2026, 1, 2, 3, 4, 5))
    assert result.output_path.exists()
    out = result.output_path.read_bytes().decode("cp1252")
    assert "[PERSONNE]" in out and "Claire Martin" not in out
