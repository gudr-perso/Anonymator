# tests/test_main_window_theme.py
from anonymator.ui.main_window import MainWindow
from anonymator.ui.model_loader import ModelLoader
from anonymator.ner import FakeNer
from anonymator.ui.theme import active_theme, set_active_theme, DEFAULT_THEME


def test_mainwindow_sets_active_theme_from_prefs(qtbot, tmp_path):
    prefs = tmp_path / "preferences.json"
    prefs.write_text('{"theme": "cap"}', encoding="utf-8")
    try:
        w = MainWindow(loader=ModelLoader(FakeNer({})), prefs_path=prefs)
        qtbot.addWidget(w)
        assert active_theme() == "cap"
    finally:
        set_active_theme(DEFAULT_THEME)


def test_theme_switch_rebuilds_and_updates_active(qtbot, tmp_path):
    prefs = tmp_path / "preferences.json"
    prefs.write_text('{"theme": "cuma"}', encoding="utf-8")
    try:
        w = MainWindow(loader=ModelLoader(FakeNer({})), prefs_path=prefs)
        qtbot.addWidget(w)
        assert active_theme() == "cuma"
        w.prefs.theme = "cap"
        w._apply_prefs()
        assert active_theme() == "cap"
        w._retheme()   # exécuter le rebuild différé de façon synchrone
        assert w.stack.count() == 7
    finally:
        set_active_theme(DEFAULT_THEME)
