# tests/test_ui_smoke.py
from unittest.mock import patch
from anonymator.ui.main_window import MainWindow


def test_main_window_builds_and_has_home(qtbot):
    with patch("anonymator.ui.main_window.is_model_available", return_value=True):
        win = MainWindow()
    qtbot.addWidget(win)
    assert win.stack.count() >= 1
    assert win.home.btn_text is not None
    assert win.home.btn_file is not None


def test_navigation_to_text_and_file(qtbot):
    with patch("anonymator.ui.main_window.is_model_available", return_value=True):
        win = MainWindow()
    qtbot.addWidget(win)
    win.show_text(); assert win.stack.currentWidget() is win.text_screen
    win.show_file(); assert win.stack.currentWidget() is win.file_screen
    win.show_home(); assert win.stack.currentWidget() is win.home


def test_starts_on_home_even_when_model_absent(qtbot):
    with patch("anonymator.ui.main_window.is_model_available", return_value=False):
        win = MainWindow()
        qtbot.addWidget(win)
        assert win.stack.currentWidget() is win.home
        assert win.home.model_card.isVisibleTo(win.home) is True


def test_request_model_navigates_to_settings(qtbot):
    with patch("anonymator.ui.main_window.is_model_available", return_value=False):
        win = MainWindow()
        qtbot.addWidget(win)
        with patch.object(win.settings_screen, "start_model_download") as start:
            win._request_model()
            assert win.stack.currentWidget() is win.settings_screen
            start.assert_called_once()


def test_model_ready_hides_invite(qtbot):
    with patch("anonymator.ui.main_window.is_model_available", return_value=False):
        win = MainWindow()
        qtbot.addWidget(win)
        win._on_model_ready()
        assert win.home.model_card.isVisibleTo(win.home) is False


def test_close_stops_download(qtbot):
    with patch("anonymator.ui.main_window.is_model_available", return_value=False):
        win = MainWindow()
        qtbot.addWidget(win)
        with patch.object(win.settings_screen, "stop_download") as stop:
            win.close()
            stop.assert_called_once()


def test_home_navcards_trigger_callbacks(qtbot):
    from anonymator.ui.home_screen import HomeScreen
    calls = []
    h = HomeScreen(lambda: calls.append("t"), lambda: calls.append("f"),
                   lambda: calls.append("s"))
    qtbot.addWidget(h)
    h.btn_text._emit(); h.btn_file._emit(); h.btn_settings._emit()
    assert calls == ["t", "f", "s"]


def test_referential_uses_prefs_overrides(qtbot, tmp_path):
    from anonymator.ui.model_loader import ModelLoader
    from anonymator.ner import FakeNer
    prefs_path = tmp_path / "prefs.json"
    prefs_path.write_text('{"theme":"cuma","entity_overrides":{"BIC":true},'
                          '"ner_stoplist":["truc"]}', encoding="utf-8")
    win = MainWindow(loader=ModelLoader(FakeNer({})), prefs_path=prefs_path)
    qtbot.addWidget(win)
    assert win.ref.is_active("BIC") is True
    assert "truc" in win.ref.ner_stoplist()
