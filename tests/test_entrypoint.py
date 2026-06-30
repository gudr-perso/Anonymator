# tests/test_entrypoint.py
from unittest.mock import patch

def test_build_app_returns_window(qtbot):
    from anonymator.__main__ import build_window
    with patch("anonymator.ui.main_window.is_model_available", return_value=True):
        win = build_window()
    qtbot.addWidget(win)
    assert win.windowTitle() == "Anonymator"
