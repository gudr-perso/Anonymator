# tests/test_home_screen.py
from anonymator.ui.home_screen import HomeScreen
from anonymator.ui.components.nav_band import NavBand


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


def test_home_has_navband(qtbot):
    h = _home(True); qtbot.addWidget(h)
    assert h.findChild(NavBand) is not None


def test_invite_description_not_truncated_in_short_window(qtbot):
    """Fenêtre peu haute : la description du bandeau était rognée sur le bas.
    Un QLabel à retour à la ligne accepte de descendre à une seule ligne, donc
    la mise en page lui prenait la hauteur qui manquait ailleurs."""
    h = _home(False); qtbot.addWidget(h)
    h.resize(1152, 420); h.show()
    qtbot.waitExposed(h)
    d = h.model_card_desc
    assert d.height() >= d.heightForWidth(d.width())


def test_invite_description_not_truncated_at_several_sizes(qtbot):
    h = _home(False); qtbot.addWidget(h)
    h.show(); qtbot.waitExposed(h)
    d = h.model_card_desc
    for size in [(1152, 400), (1152, 700), (900, 480), (1400, 900)]:
        h.resize(*size)
        qtbot.wait(30)
        need = d.heightForWidth(d.width())
        assert d.height() >= need, f"tronqué en {size}"
        # ...sans pour autant absorber la place libre en grande fenêtre.
        assert d.height() <= need + 4, f"étiré inutilement en {size}"


def test_invite_announces_real_download_size(qtbot):
    from anonymator.core.model_status import MODEL_DOWNLOAD_SIZE
    h = _home(False); qtbot.addWidget(h)
    txt = h.model_card_desc.text()
    assert MODEL_DOWNLOAD_SIZE in txt
    assert "300 Mo" not in txt
