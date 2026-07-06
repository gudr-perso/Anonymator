from unittest.mock import patch

from anonymator.referential import Referential
from anonymator.ui.preferences import Preferences
from anonymator.ui.settings_screen import SettingsScreen, _TYPES


def test_changing_theme_updates_prefs_and_calls_apply(qtbot):
    prefs = Preferences()
    called = []
    s = SettingsScreen(Referential.load_default(), prefs,
                       on_apply=lambda: called.append(True), on_back=lambda: None)
    qtbot.addWidget(s)
    s.select_theme("cap")
    assert prefs.theme == "cap"
    assert called  # on_apply déclenché → réapplique le QSS + sauvegarde


def test_theme_combobox_selection_sets_prefs(qtbot):
    prefs = Preferences()
    s = SettingsScreen(Referential.load_default(), prefs,
                       on_apply=lambda: None, on_back=lambda: None)
    qtbot.addWidget(s)
    s.theme_box.setCurrentText("CAP — bleu")
    assert prefs.theme == "cap"


def test_toggle_entity_type_updates_overrides(qtbot):
    prefs = Preferences(); called = []
    s = SettingsScreen(Referential.load_default(), prefs,
                       on_apply=lambda: called.append(True), on_back=lambda: None)
    qtbot.addWidget(s)
    s.set_type_active("BIC", True)
    assert prefs.entity_overrides["BIC"] is True and called


def test_one_entity_card_per_type(qtbot):
    s = _settings()
    qtbot.addWidget(s)
    assert len(s._type_toggles) == len(_TYPES) == 14


def test_count_badge_shows_active_count(qtbot):
    s = _settings()
    qtbot.addWidget(s)
    n_active = sum(1 for code in _TYPES if s.ref.is_active(code))
    assert s.count_badge.text() == f"{n_active} / 14 actifs"


def test_toggling_a_type_via_toggle_widget_updates_prefs_and_apply(qtbot):
    prefs = Preferences(); called = []
    s = SettingsScreen(Referential.load_default(), prefs,
                       on_apply=lambda: called.append(True), on_back=lambda: None)
    qtbot.addWidget(s)
    s._type_toggles["PERSON"].setChecked(False)
    assert prefs.entity_overrides["PERSON"] is False
    assert called


def test_toggling_a_type_refreshes_counter(qtbot):
    s = _settings()
    qtbot.addWidget(s)
    s._type_toggles["PERSON"].setChecked(True)
    n_active = sum(1 for code in _TYPES if s.ref.is_active(code) or code == "PERSON")
    assert s.count_badge.text() == f"{n_active} / 14 actifs"


def _settings(prefs=None):
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


def test_theme_selector_hidden_when_brand_locked(qtbot):
    from anonymator.brand import lock_brand, reset_brand
    try:
        lock_brand("cap")
        s = _settings(); qtbot.addWidget(s)
        assert not hasattr(s, "theme_box")
    finally:
        reset_brand()


def test_theme_selector_present_in_dev(qtbot):
    from anonymator.brand import reset_brand
    reset_brand()
    s = _settings(); qtbot.addWidget(s)
    assert hasattr(s, "theme_box")
