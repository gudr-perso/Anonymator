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
