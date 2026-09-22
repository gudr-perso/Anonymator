from anonymator.ui.about_screen import AboutScreen, EMBEDDED_COMPONENTS
from anonymator.brand import lock_brand, reset_brand
from anonymator import __version__


def test_shows_version(qtbot):
    scr = AboutScreen(on_back=lambda: None)
    qtbot.addWidget(scr)
    assert __version__ in scr.version_badge.text()


def test_embedded_components_listed():
    names = [c[0] for c in EMBEDDED_COMPONENTS]
    assert "PyMuPDF" in names
    assert "GLiNER" in names


def teardown_function():
    reset_brand()


def test_contact_button(qtbot):
    scr = AboutScreen(on_back=lambda: None)
    qtbot.addWidget(scr)
    assert scr.contact_btn is not None


def test_pas_de_contact_sans_formulaire(qtbot, monkeypatch):
    import anonymator.brand as brand
    from dataclasses import replace
    monkeypatch.setitem(brand.BRANDS, "cuma", replace(brand.BRANDS["cuma"], form_url=None))
    lock_brand("cuma")
    scr = AboutScreen(on_back=lambda: None)
    qtbot.addWidget(scr)
    assert scr.contact_btn is None


def test_back_navband(qtbot):
    from anonymator.ui.components.nav_band import NavBand
    called = []
    scr = AboutScreen(on_back=lambda: called.append(True))
    qtbot.addWidget(scr)
    nb = scr.findChild(NavBand)
    assert nb is not None
    nb.home_btn.click()
    assert called == [True]
