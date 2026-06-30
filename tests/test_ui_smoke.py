from anonymator.ui.main_window import MainWindow


def test_main_window_builds_and_has_home(qtbot):
    win = MainWindow()
    qtbot.addWidget(win)
    assert win.stack.count() >= 1
    assert win.home.btn_text is not None
    assert win.home.btn_file is not None


def test_navigation_to_text_and_file(qtbot):
    win = MainWindow()
    qtbot.addWidget(win)
    win.show_text()
    assert win.stack.currentWidget() is win.text_screen
    win.show_file()
    assert win.stack.currentWidget() is win.file_screen
    win.show_home()
    assert win.stack.currentWidget() is win.home
