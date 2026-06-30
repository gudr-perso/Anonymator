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


def _screen(loader_map=None):
    ref = Referential.load_default()
    loader = ModelLoader(FakeNer(loader_map or {}))
    return FileScreen(ref, loader, Preferences(), on_back=lambda: None)


def test_preview_splits_columns(qtbot, tmp_path):
    src = tmp_path / "f.csv"
    src.write_bytes("Nom;Montant\nClaire Martin;100,00\n".encode("cp1252"))
    s = _screen(); qtbot.addWidget(s)
    s.load_path(str(src))
    assert s.table.columnCount() == 2
    assert s.table.horizontalHeaderItem(0).text() == "Nom"
    assert s.table.item(0, 0).text() == "Claire Martin"


def test_analyze_builds_session_and_side(qtbot, tmp_path):
    src = tmp_path / "f.csv"
    src.write_bytes("Nom;Montant\nClaire Martin;100,00\nPaul Durand;50,00\n".encode("cp1252"))
    s = _screen({"Claire Martin": "PERSON", "Paul Durand": "PERSON"})
    qtbot.addWidget(s)
    s.load_path(str(src))
    s.analyze()
    qtbot.waitUntil(lambda: s.session is not None, timeout=5000)
    assert s.session.count_retained("PERSON") == 2
    assert s.side.topLevelItemCount() == 1            # un type : PERSON
    assert s.side.topLevelItem(0).childCount() == 2   # deux valeurs distinctes


def test_pagination_navigates(qtbot, tmp_path):
    lines = "Nom;Montant\n" + "".join(f"Nom{i};1,00\n" for i in range(45))
    src = tmp_path / "big.csv"; src.write_bytes(lines.encode("cp1252"))
    s = _screen(); qtbot.addWidget(s)
    s.load_path(str(src)); s.analyze()
    qtbot.waitUntil(lambda: s.session is not None, timeout=5000)
    assert s._page_count() == 3            # 45 lignes / 20
    s._go(99)                              # clampé à la dernière
    assert s.page == 2
    assert s.table.rowCount() == 5         # 45 - 40
    s._go(0)
    assert s.table.rowCount() == 20


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
