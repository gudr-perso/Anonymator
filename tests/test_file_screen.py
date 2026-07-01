from datetime import datetime
from unittest.mock import patch
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
    worker = FileScanWorker(doc, ModelLoader(FakeNer({"Claire Martin": "PERSON"})),
                            Referential.load_default(), cols)
    with qtbot.waitSignal(worker.scan_finished, timeout=5000) as blocker:
        worker.start()
    worker.wait()           # ensure thread finishes before teardown
    scanned = blocker.args[0]
    assert (1, 0) in scanned


def test_scan_worker_emits_error_when_detector_load_fails(qtbot, tmp_path):
    """Le détecteur est construit DANS le thread : un échec de chargement
    remonte via `error` au lieu d'exploser en silence sur le thread principal."""
    src = tmp_path / "f.csv"
    src.write_bytes("Nom;Montant\nClaire Martin;100,00\n".encode("cp1252"))
    doc = csv_io.read_csv(src)
    cols = default_maskable_columns(doc.rows, doc.has_header)

    class BoomLoader:
        def get(self):
            raise RuntimeError("échec chargement modèle")

    worker = FileScanWorker(doc, BoomLoader(), Referential.load_default(), cols)
    with qtbot.waitSignal(worker.error, timeout=5000) as blocker:
        worker.start()
    worker.wait()
    assert "échec chargement modèle" in blocker.args[0]


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


def test_apply_review_writes_user_choices(qtbot, tmp_path):
    src = tmp_path / "f.csv"
    src.write_bytes("Nom;Montant\nClaire Martin;100,00\nPaul Durand;50,00\n".encode("cp1252"))
    ref = Referential.load_default()
    loader = ModelLoader(FakeNer({"Claire Martin": "PERSON", "Paul Durand": "PERSON"}))
    s = FileScreen(ref, loader, Preferences(output_dir=str(tmp_path)), on_back=lambda: None)
    qtbot.addWidget(s)
    s.load_path(str(src)); s.analyze()
    qtbot.waitUntil(lambda: s.session is not None, timeout=5000)
    s.session.set_value_enabled("PERSON", "Paul Durand", False)   # keep Paul in clear
    res = s.run(when=datetime(2026, 1, 2, 3, 4, 5))
    out = res.output_path.read_bytes().decode("cp1252")
    assert "[PERSONNE]" in out and "Paul Durand" in out and "Claire Martin" not in out


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


def test_run_clicked_without_session_threads_and_confirms(qtbot, tmp_path):
    """Sans analyse préalable (pas de session), « Anonymiser » passe par un
    worker : overlay affiché, confirmation à la fin, fichier écrit."""
    src = tmp_path / "f.csv"
    src.write_bytes("Nom;Montant\nClaire Martin;100,00\n".encode("cp1252"))
    loader = ModelLoader(FakeNer({"Claire Martin": "PERSON"}))
    s = FileScreen(Referential.load_default(), loader,
                   Preferences(output_dir=str(tmp_path)), on_back=lambda: None)
    qtbot.addWidget(s)
    s.load_path(str(src))
    assert s.session is None
    with patch("anonymator.ui.file_screen.QMessageBox.information") as info:
        s._run_clicked()
        qtbot.waitUntil(lambda: info.called, timeout=5000)
    assert info.called
    outs = list(tmp_path.glob("*_ano_*.csv"))
    assert outs and outs[0].read_bytes().decode("cp1252").count("[PERSONNE]") == 1


def test_run_clicked_surfaces_detector_load_failure(qtbot, tmp_path):
    """Régression : un échec de chargement du modèle sur le chemin direct
    affiche un dialogue explicite au lieu d'un plantage silencieux."""
    src = tmp_path / "f.csv"
    src.write_bytes("Nom;Montant\nClaire Martin;100,00\n".encode("cp1252"))

    class BoomLoader:
        def has_detector(self):
            return True

        def get(self):
            raise RuntimeError("échec chargement modèle")

    s = FileScreen(Referential.load_default(), BoomLoader(),
                   Preferences(output_dir=str(tmp_path)), on_back=lambda: None)
    qtbot.addWidget(s)
    s.load_path(str(src))
    with patch("anonymator.ui.file_screen.QMessageBox.warning") as warn:
        s._run_clicked()
        qtbot.waitUntil(lambda: warn.called, timeout=5000)
    assert warn.called


def test_review_disabled_for_xlsx(qtbot, tmp_path):
    src = tmp_path / "f.xlsx"; src.write_bytes(b"PK\x03\x04stub")   # extension xlsx
    s = _screen(); qtbot.addWidget(s)
    s.load_path(str(src))
    assert s.btn_review.isEnabled() is False


def test_txt_routes_to_text_review(qtbot, tmp_path):
    called = {}
    ref = Referential.load_default()
    s = FileScreen(ref, ModelLoader(FakeNer({})), Preferences(),
                   on_back=lambda: None,
                   on_text_review=lambda text: called.setdefault("text", text))
    qtbot.addWidget(s)
    src = tmp_path / "n.txt"; src.write_text("Bonjour Claire", encoding="utf-8")
    s.load_path(str(src))
    s.analyze()
    assert called.get("text") == "Bonjour Claire"


def test_busy_overlay_toggles(qtbot):
    s = _screen(); qtbot.addWidget(s); s.show()
    assert s._overlay.isVisible() is False
    s._set_busy(True)
    assert s._overlay.isVisible() is True
    assert s._overlay.text() == "⏳  Analyse en cours…"
    s._set_busy(False)
    assert s._overlay.isVisible() is False


def test_file_degraded_banner_when_model_absent(qtbot, tmp_path):
    src = tmp_path / "f.csv"
    src.write_bytes("Nom;IBAN\nClaire Martin;FR7630006000011234567890189\n".encode("cp1252"))
    with patch("anonymator.ui.file_screen.is_model_available", return_value=False):
        s = FileScreen(Referential.load_default(), ModelLoader(), Preferences(),
                       on_back=lambda: None, on_request_model=lambda: None)
        qtbot.addWidget(s)
        s.load_path(str(src))
        s.analyze()
        qtbot.waitUntil(lambda: s.session is not None, timeout=5000)
        assert s._degraded is True
        assert s.banner.isVisibleTo(s) is True


def test_file_no_banner_with_injected_detector(qtbot, tmp_path):
    src = tmp_path / "f.csv"
    src.write_bytes("Nom;Montant\nClaire Martin;100,00\n".encode("cp1252"))
    with patch("anonymator.ui.file_screen.is_model_available", return_value=False):
        s = FileScreen(Referential.load_default(),
                       ModelLoader(FakeNer({"Claire Martin": "PERSON"})),
                       Preferences(), on_back=lambda: None)
        qtbot.addWidget(s)
        s.load_path(str(src)); s.analyze()
        qtbot.waitUntil(lambda: s.session is not None, timeout=5000)
        assert s._degraded is False
        assert s.banner.isVisibleTo(s) is False
