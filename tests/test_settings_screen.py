from unittest.mock import patch

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


def test_add_and_remove_rule(qtbot, tmp_path):
    from anonymator.referential import Referential
    from anonymator.ui.preferences import Preferences
    from anonymator.ui.settings_screen import SettingsScreen
    from anonymator.user_rules import UserRules
    rules_path = tmp_path / "user_rules.json"
    UserRules([]).save(rules_path)
    prefs = Preferences()
    s = SettingsScreen(Referential.load_default(), prefs,
                       on_apply=lambda: None, on_back=lambda: None,
                       rules_path=rules_path)
    qtbot.addWidget(s)
    s.add_rule(mode="simple", pattern="FACT#######", action="keep", note="factures")
    assert s.user_rules.keep_matches("FACT1234567")
    rule = s.user_rules.rules[0]
    s.remove_rule(rule)
    assert not s.user_rules.keep_matches("FACT1234567")


def _settings(prefs=None):
    from anonymator.referential import Referential
    from anonymator.ui.preferences import Preferences
    from anonymator.ui.settings_screen import SettingsScreen
    return SettingsScreen(Referential.load_default(), prefs or Preferences(),
                          on_apply=lambda: None, on_back=lambda: None)

def test_model_status_absent(qtbot):
    with patch("anonymator.ui.settings_screen.is_model_available", return_value=False):
        s = _settings(); qtbot.addWidget(s)
        assert "non installé" in s.model_status_label.text().lower()
        assert s.btn_model.text() == "Télécharger"

def test_model_status_present(qtbot):
    with patch("anonymator.ui.settings_screen.is_model_available", return_value=True), \
         patch("anonymator.ui.settings_screen.installed_size", return_value=300 * 1024 * 1024):
        s = _settings(); qtbot.addWidget(s)
        assert "installé" in s.model_status_label.text().lower()
        assert s.btn_model.text() == "Réparer (re-télécharger)"

def test_model_progress_updates_bar(qtbot):
    with patch("anonymator.ui.settings_screen.is_model_available", return_value=False):
        s = _settings(); qtbot.addWidget(s)
        s._on_model_progress(150 * 1024 * 1024, 300 * 1024 * 1024)
        assert s.model_progress.maximum() == 300 * 1024 * 1024
        assert s.model_progress.value() == 150 * 1024 * 1024

def test_model_finished_emits_ready(qtbot):
    with patch("anonymator.ui.settings_screen.is_model_available", return_value=False):
        s = _settings(); qtbot.addWidget(s)
        ready = []
        s.model_ready.connect(lambda: ready.append(True))
        with patch("anonymator.ui.settings_screen.is_model_available", return_value=True), \
             patch("anonymator.ui.settings_screen.installed_size", return_value=10):
            s._on_model_finished()
        assert ready == [True]
        assert "installé" in s.model_status_label.text().lower()


def test_settings_shows_about_section(qtbot):
    import anonymator
    s = _settings(); qtbot.addWidget(s)
    text = s.about_label.text()
    assert "AGPL-3.0" in text
    assert f"Anonymator v{anonymator.__version__}" in text
    assert "github.com/gudr-perso/Anonymator" in text
