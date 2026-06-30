from anonymator.ui.setup_screen import SetupScreen


def test_setup_screen_builds(qtbot):
    s = SetupScreen()
    qtbot.addWidget(s)
    assert s.btn_start is not None
    assert s.label_status is not None


def test_on_download_finished_emits_model_ready(qtbot):
    """Appelle _on_download_finished directement pour éviter le vrai téléchargement."""
    s = SetupScreen()
    qtbot.addWidget(s)
    ready = []
    s.model_ready.connect(lambda: ready.append(True))
    s._on_download_finished()
    assert ready
