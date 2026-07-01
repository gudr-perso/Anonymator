# tests/test_entrypoint.py
import sys
from unittest.mock import patch

def test_build_app_returns_window(qtbot):
    from anonymator.__main__ import build_window
    with patch("anonymator.ui.main_window.is_model_available", return_value=True):
        win = build_window()
    qtbot.addWidget(win)
    assert win.windowTitle() == "Anonymator"


def test_ensure_std_streams_replaces_none(monkeypatch):
    from anonymator.__main__ import ensure_std_streams
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)
    ensure_std_streams()
    assert sys.stdout is not None and hasattr(sys.stdout, "write")
    assert sys.stderr is not None and hasattr(sys.stderr, "write")
