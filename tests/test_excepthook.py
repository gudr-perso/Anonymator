# tests/test_excepthook.py
import sys
from unittest.mock import patch
from anonymator.__main__ import install_excepthook, _excepthook


def test_install_sets_excepthook():
    original = sys.excepthook
    try:
        install_excepthook()
        assert sys.excepthook is _excepthook
    finally:
        sys.excepthook = original


def test_excepthook_shows_message_box(qtbot):
    """Toute exception non gérée déclenche un dialogue d'erreur explicite —
    c'est la garantie « message d'erreur explicite » qui manquait dans l'exe."""
    with patch("anonymator.__main__.QMessageBox.critical") as crit:
        try:
            raise ValueError("boom détaillé")
        except ValueError:
            _excepthook(*sys.exc_info())
    assert crit.called
    shown = " ".join(str(a) for a in crit.call_args.args)
    assert "ValueError" in shown or "boom détaillé" in shown


def test_excepthook_writes_crash_log(qtbot, tmp_path):
    log = tmp_path / "crash.log"
    with patch("anonymator.__main__._CRASH_LOG", log), \
         patch("anonymator.__main__.QMessageBox.critical"):
        try:
            raise RuntimeError("trace à journaliser")
        except RuntimeError:
            _excepthook(*sys.exc_info())
    assert log.exists()
    assert "trace à journaliser" in log.read_text(encoding="utf-8")
