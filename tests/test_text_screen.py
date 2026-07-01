from anonymator.referential import Referential
from anonymator.ner import FakeNer
from anonymator.ui.model_loader import ModelLoader
from anonymator.ui.preferences import Preferences
from anonymator.ui.text_screen import TextScreen


def _screen():
    ref = Referential.load_default()
    loader = ModelLoader(FakeNer({"Claire Martin": "PERSON"}))
    return TextScreen(ref, loader, Preferences(), on_back=lambda: None)


def _analyze(qtbot, s):
    """Lance l'analyse (asynchrone) et attend la fin du worker."""
    s.analyze()
    qtbot.waitUntil(lambda: s.session is not None, timeout=5000)


def test_analyze_populates_session(qtbot):
    s = _screen(); qtbot.addWidget(s)
    s.input.setPlainText("Claire Martin mail c@x.fr")
    _analyze(qtbot, s)
    types = {e.type for e in s.session.entities()}
    assert {"PERSON", "EMAIL"} <= types


def test_apply_produces_masked_text(qtbot):
    s = _screen(); qtbot.addWidget(s)
    s.input.setPlainText("Claire Martin mail c@x.fr")
    _analyze(qtbot, s); s.apply()
    assert s.output.toPlainText() == "[PERSONNE] mail [EMAIL]"


def test_stats_update_after_analyze(qtbot):
    s = _screen(); qtbot.addWidget(s)
    s.input.setPlainText("Claire Martin mail c@x.fr")
    _analyze(qtbot, s)
    assert s.stat_detected.value_label.text() == "2"
    assert s.stat_risk.value_label.text() == "Élevé"


from unittest.mock import patch
from anonymator.ui.text_screen import TextScreen
from anonymator.ui.model_loader import ModelLoader
from anonymator.ui.preferences import Preferences
from anonymator.referential import Referential
from anonymator.ner import FakeNer


def test_degraded_banner_when_model_absent(qtbot):
    with patch("anonymator.ui.text_screen.is_model_available", return_value=False):
        s = TextScreen(Referential.load_default(), ModelLoader(), Preferences(),
                       on_back=lambda: None, on_request_model=lambda: None)
        qtbot.addWidget(s)
        s.input.setPlainText("IBAN FR76 3000 6000 0112 3456 7890 189 pour Claire Martin")
        s.analyze()
        qtbot.waitUntil(lambda: s.session is not None, timeout=5000)
        assert s._degraded is True
        assert s.banner.isVisibleTo(s) is True
        assert any(e.type == "IBAN" for e in s.session.entities())


def test_no_banner_when_detector_injected(qtbot):
    with patch("anonymator.ui.text_screen.is_model_available", return_value=False):
        s = TextScreen(Referential.load_default(),
                       ModelLoader(FakeNer({"Claire Martin": "PERSON"})),
                       Preferences(), on_back=lambda: None)
        qtbot.addWidget(s)
        s.input.setPlainText("Bonjour Claire Martin")
        s.analyze()
        qtbot.waitUntil(lambda: s.session is not None, timeout=5000)
        assert s._degraded is False
        assert s.banner.isVisibleTo(s) is False


def test_banner_install_calls_request_model(qtbot):
    called = []
    with patch("anonymator.ui.text_screen.is_model_available", return_value=False):
        s = TextScreen(Referential.load_default(), ModelLoader(), Preferences(),
                       on_back=lambda: None, on_request_model=lambda: called.append(True))
        qtbot.addWidget(s)
        s.banner.btn.click()
    assert called == [True]
