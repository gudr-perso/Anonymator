# tests/test_model_loader.py
from anonymator.ui.model_loader import ModelLoader
from anonymator.ner import FakeNer


def test_has_detector_true_when_injected():
    assert ModelLoader(FakeNer({})).has_detector() is True


def test_has_detector_false_when_lazy():
    assert ModelLoader().has_detector() is False
