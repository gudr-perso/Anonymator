import anonymator
from anonymator.ui.about_screen import AboutScreen


def test_about_screen_shows_legal_lines(qtbot):
    s = AboutScreen(on_back=lambda: None)
    qtbot.addWidget(s)
    text = s.about_label.text()
    assert "AGPL-3.0" in text
    assert f"Anonymator v{anonymator.__version__}" in text
    assert "github.com/gudr-perso/Anonymator" in text


def test_about_screen_back_button_calls_on_back(qtbot):
    called = []
    s = AboutScreen(on_back=lambda: called.append(True))
    qtbot.addWidget(s)
    s.back_btn.click()
    assert called
