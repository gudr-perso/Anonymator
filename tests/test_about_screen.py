from anonymator.ui.about_screen import AboutScreen, EMBEDDED_COMPONENTS
from anonymator import __version__


def test_shows_version(qtbot):
    scr = AboutScreen(on_back=lambda: None)
    qtbot.addWidget(scr)
    assert __version__ in scr.version_badge.text()


def test_embedded_components_listed():
    names = [c[0] for c in EMBEDDED_COMPONENTS]
    assert "PyMuPDF" in names
    assert "GLiNER" in names


def test_back_navband(qtbot):
    from anonymator.ui.components.nav_band import NavBand
    called = []
    scr = AboutScreen(on_back=lambda: called.append(True))
    qtbot.addWidget(scr)
    nb = scr.findChild(NavBand)
    assert nb is not None
    nb.home_btn.click()
    assert called == [True]
