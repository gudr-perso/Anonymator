# tests/test_ui_smoke.py
from unittest.mock import patch
from anonymator.ui.main_window import MainWindow

def test_main_window_builds_and_has_home(qtbot):
    win = MainWindow(skip_setup=True)
    qtbot.addWidget(win)
    assert win.stack.count() >= 1
    assert win.home.btn_text is not None
    assert win.home.btn_file is not None

def test_navigation_to_text_and_file(qtbot):
    win = MainWindow(skip_setup=True)
    qtbot.addWidget(win)
    win.show_text()
    assert win.stack.currentWidget() is win.text_screen
    win.show_file()
    assert win.stack.currentWidget() is win.file_screen
    win.show_home()
    assert win.stack.currentWidget() is win.home

def test_main_window_shows_setup_when_model_absent(qtbot):
    with patch("anonymator.ui.main_window.is_model_available", return_value=False):
        win = MainWindow()
        qtbot.addWidget(win)
        assert win.stack.currentWidget() is win.setup_screen

def test_main_window_skips_setup_when_model_present(qtbot):
    with patch("anonymator.ui.main_window.is_model_available", return_value=True):
        win = MainWindow()
        qtbot.addWidget(win)
        assert win.stack.currentWidget() is win.home
