# tests/test_home_screen.py
from anonymator.ui.home_screen import HomeScreen


def _home(model_available, dl=None, later=None):
    return HomeScreen(lambda: None, lambda: None, lambda: None,
                      model_available=model_available,
                      on_download=dl or (lambda: None),
                      on_dismiss=later or (lambda: None))


def test_invite_visible_when_model_absent(qtbot):
    h = _home(False); qtbot.addWidget(h)
    assert h.model_card.isVisibleTo(h) is True


def test_invite_hidden_when_model_present(qtbot):
    h = _home(True); qtbot.addWidget(h)
    assert h.model_card.isVisibleTo(h) is False


def test_invite_download_and_dismiss(qtbot):
    calls = []
    h = _home(False, dl=lambda: calls.append("dl"), later=lambda: calls.append("later"))
    qtbot.addWidget(h)
    h.btn_model_download.click()
    h.btn_model_later.click()
    assert calls == ["dl", "later"]
    assert h.model_card.isVisibleTo(h) is False


def test_set_model_available_hides_card(qtbot):
    h = _home(False); qtbot.addWidget(h)
    h.set_model_available(True)
    assert h.model_card.isVisibleTo(h) is False


def test_navcards_still_callable_with_defaults(qtbot):
    calls = []
    h = HomeScreen(lambda: calls.append("t"), lambda: calls.append("f"),
                   lambda: calls.append("s"))
    qtbot.addWidget(h)
    h.btn_text._emit(); h.btn_file._emit(); h.btn_settings._emit()
    assert calls == ["t", "f", "s"]


def test_rules_card_triggers_callback(qtbot):
    clicked = []
    h = HomeScreen(lambda: None, lambda: None, lambda: None,
                   on_rules=lambda: clicked.append(True))
    qtbot.addWidget(h)
    h.btn_rules.click()
    assert clicked


def test_about_card_triggers_callback(qtbot):
    clicked = []
    h = HomeScreen(lambda: None, lambda: None, lambda: None,
                   on_about=lambda: clicked.append(True))
    qtbot.addWidget(h)
    h.btn_about.click()
    assert clicked
