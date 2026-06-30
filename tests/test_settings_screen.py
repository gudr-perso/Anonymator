from anonymator.referential import Referential
from anonymator.ui.preferences import Preferences
from anonymator.ui.settings_screen import SettingsScreen


def test_changing_theme_updates_prefs_and_calls_apply(qtbot):
    prefs = Preferences()
    called = []
    s = SettingsScreen(Referential.load_default(), prefs,
                       on_apply=lambda: called.append(True), on_back=lambda: None)
    qtbot.addWidget(s)
    s.select_theme("cap")
    assert prefs.theme == "cap"
    assert called  # on_apply déclenché → réapplique le QSS + sauvegarde
