from anonymator.ui.components.nav_band import NavBand
from anonymator.ui.about_screen import AboutScreen
from anonymator.ui.rules_screen import RulesScreen


def test_about_has_navband(qtbot):
    scr = AboutScreen(on_back=lambda: None); qtbot.addWidget(scr)
    assert scr.findChild(NavBand) is not None


def test_rules_has_navband(qtbot, tmp_path):
    scr = RulesScreen(tmp_path / "r.json", on_apply=lambda: None, on_back=lambda: None)
    qtbot.addWidget(scr)
    assert scr.findChild(NavBand) is not None
