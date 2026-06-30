def test_build_app_returns_window(qtbot):
    from anonymator.__main__ import build_window
    win = build_window()
    qtbot.addWidget(win)
    assert win.windowTitle() == "Anonymator"
