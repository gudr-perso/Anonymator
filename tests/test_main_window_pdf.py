# tests/test_main_window_pdf.py
from unittest.mock import patch
from anonymator.ui.main_window import MainWindow


def test_main_window_has_pdf_screen(qtbot, tmp_path):
    with patch("anonymator.ui.main_window.is_model_available", return_value=True):
        w = MainWindow(prefs_path=tmp_path / "p.json")
        qtbot.addWidget(w)
    assert hasattr(w, "pdf_screen")
    w.show_pdf()
    assert w.stack.currentWidget() is w.pdf_screen


def test_apply_prefs_updates_pdf_ref(qtbot, tmp_path):
    with patch("anonymator.ui.main_window.is_model_available", return_value=True):
        w = MainWindow(prefs_path=tmp_path / "p.json")
        qtbot.addWidget(w)
    sentinel = object()
    w.ref = sentinel
    with patch.object(w, "_build_ref", return_value=sentinel):
        w._apply_prefs()
    assert w.pdf_screen.ref is sentinel


def test_home_has_pdf_card(qtbot):
    from anonymator.ui.home_screen import HomeScreen
    calls = {}
    h = HomeScreen(lambda: None, lambda: None, lambda: None,
                   on_pdf=lambda: calls.setdefault("pdf", True))
    qtbot.addWidget(h)
    h.btn_pdf.click()
    assert calls.get("pdf") is True
