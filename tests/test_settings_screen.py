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


def test_toggle_entity_type_updates_overrides(qtbot):
    from anonymator.referential import Referential
    from anonymator.ui.preferences import Preferences
    from anonymator.ui.settings_screen import SettingsScreen
    prefs = Preferences(); called = []
    s = SettingsScreen(Referential.load_default(), prefs,
                       on_apply=lambda: called.append(True), on_back=lambda: None)
    qtbot.addWidget(s)
    s.set_type_active("BIC", True)
    assert prefs.entity_overrides["BIC"] is True and called


def test_add_and_remove_stoplist_term(qtbot):
    from anonymator.referential import Referential
    from anonymator.ui.preferences import Preferences
    from anonymator.ui.settings_screen import SettingsScreen
    prefs = Preferences()
    s = SettingsScreen(Referential.load_default(), prefs,
                       on_apply=lambda: None, on_back=lambda: None)
    qtbot.addWidget(s)
    s.add_stop_term("service client")
    assert "service client" in prefs.ner_stoplist
    s.remove_stop_term("service client")
    assert "service client" not in prefs.ner_stoplist
