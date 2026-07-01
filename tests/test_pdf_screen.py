# tests/test_pdf_screen.py
from datetime import datetime
from unittest.mock import patch
import fitz
from tests.pdf_fixtures import make_native_pdf, make_scanned_pdf
from anonymator.referential import Referential
from anonymator.ner import FakeNer
from anonymator.ui.model_loader import ModelLoader
from anonymator.ui.preferences import Preferences
from anonymator.ui.pdf_screen import PdfScreen


def _screen(mapping=None, out=None):
    ref = Referential.load_default()
    loader = ModelLoader(FakeNer(mapping or {}))
    prefs = Preferences(output_dir=str(out)) if out else Preferences()
    return PdfScreen(ref, loader, prefs, on_back=lambda: None)


def test_load_enables_analyze(qtbot, tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "Contact Claire Martin ici")
    s = _screen(); qtbot.addWidget(s)
    s.load_path(str(src))
    assert s.btn_review.isEnabled() is True


def test_busy_overlay_toggles(qtbot):
    s = _screen(); qtbot.addWidget(s); s.show()
    assert s._overlay.isVisible() is False
    s._set_busy(True)
    assert s._overlay.isVisible() is True
    assert s._overlay.text() == "⏳  Analyse en cours…"
    s._set_busy(False)
    assert s._overlay.isVisible() is False


def test_analyze_builds_session_and_side(qtbot, tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "Contact Claire Martin ici")
    s = _screen({"Claire Martin": "PERSON"}); qtbot.addWidget(s)
    s.load_path(str(src)); s.analyze()
    qtbot.waitUntil(lambda: s.session is not None, timeout=5000)
    assert s.session.count_retained("PERSON") == 1
    assert s.side.topLevelItemCount() == 1


def test_redact_run_writes_destroyed_pdf(qtbot, tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "Contact Claire Martin ici")
    s = _screen({"Claire Martin": "PERSON"}, out=tmp_path); qtbot.addWidget(s)
    s.load_path(str(src)); s.analyze()
    qtbot.waitUntil(lambda: s.session is not None, timeout=5000)
    res = s.run_redact(when=datetime(2026, 1, 2, 3, 4, 5))
    assert res.output_path.suffix == ".pdf"
    check = fitz.open(str(res.output_path))
    assert "Claire Martin" not in check[0].get_text()
    check.close()


def test_text_run_writes_masked_txt(qtbot, tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "Contact Claire Martin ici")
    s = _screen({"Claire Martin": "PERSON"}, out=tmp_path); qtbot.addWidget(s)
    s.load_path(str(src))
    res = s.run_text(when=datetime(2026, 1, 2, 3, 4, 5))
    assert res.output_path.suffix == ".txt"
    out = res.output_path.read_text(encoding="utf-8")
    assert "[PERSONNE]" in out and "Claire Martin" not in out


def test_manual_rect_added_to_session(qtbot, tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "Contact Claire Martin ici")
    s = _screen({"Claire Martin": "PERSON"}); qtbot.addWidget(s)
    s.load_path(str(src)); s.analyze()
    qtbot.waitUntil(lambda: s.session is not None, timeout=5000)
    s._on_manual_rect((300.0, 300.0, 360.0, 330.0))
    assert (300.0, 300.0, 360.0, 330.0) in s.session.manual_rects(0)


def test_scanned_pdf_shows_error(qtbot, tmp_path):
    src = make_scanned_pdf(tmp_path / "s.pdf")
    s = _screen(); qtbot.addWidget(s)
    s.load_path(str(src))
    with patch("anonymator.ui.pdf_screen.QMessageBox.warning") as warn:
        s.analyze()
        qtbot.waitUntil(lambda: warn.called, timeout=5000)
    assert warn.called
