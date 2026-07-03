from PySide6.QtGui import QIcon
from anonymator.ui.icons import icon, ICON_NAMES

def test_icons_load(qtbot):
    for name in ICON_NAMES:
        ic = icon(name)
        assert isinstance(ic, QIcon)
        assert not ic.isNull()

from anonymator.ui.components.toggle import ToggleSwitch

def test_toggle_switch(qtbot):
    t = ToggleSwitch(); qtbot.addWidget(t)
    assert t.isChecked() is False
    states = []
    t.toggled.connect(states.append)
    t.setChecked(True)
    assert t.isChecked() is True and states == [True]

from anonymator.ui.components.badge import CategoryBadge
from anonymator.ui.colors import color_for

def test_category_badge(qtbot):
    b = CategoryBadge("PERSON", "NOM"); qtbot.addWidget(b)
    assert b.text() == "NOM"
    assert color_for("PERSON").lstrip("#").lower() in b.styleSheet().lower()

from anonymator.ui.components.cards import Card, StatCard, NavCard

def test_stat_card(qtbot):
    s = StatCard("layers", "Catégories"); qtbot.addWidget(s)
    s.set_value("6")
    assert s.value_label.text() == "6"

def test_nav_card_clicked(qtbot):
    clicks = []
    n = NavCard("document", "Coller du texte", "Analyser un texte", on_click=lambda: clicks.append(1))
    qtbot.addWidget(n)
    n._emit()
    assert clicks == [1]

def test_card_title(qtbot):
    c = Card("shield", "Entités détectées"); qtbot.addWidget(c)
    assert "Entités détectées" in c.title_label.text()

from PySide6.QtWidgets import QLabel
from anonymator.ui.components.header import HeaderBand

def test_header_band(qtbot):
    h = HeaderBand(); qtbot.addWidget(h)
    assert h.objectName() == "HeaderBand"
    labels = [w.text() for w in h.findChildren(QLabel)]
    assert "Anonymator" in labels
    assert any("CUMA" in t for t in labels)

def test_model_banner_install_callback(qtbot):
    from anonymator.ui.components.banner import ModelBanner
    called = []
    b = ModelBanner(on_install=lambda: called.append(True))
    qtbot.addWidget(b)
    b.btn.click()
    assert called == [True]

from anonymator.ui.theme import set_active_theme, DEFAULT_THEME
from anonymator.ui.components.toggle import ToggleSwitch as _Toggle


def test_toggle_track_color_follows_theme(qtbot):
    from anonymator.ui.theme import color
    try:
        set_active_theme("cap")
        t = _Toggle(); qtbot.addWidget(t)
        t.setChecked(True)
        assert t.track_color() == color("action")   # cyan en CAP
        t.setChecked(False)
        assert t.track_color() == color("toggle_off")
    finally:
        set_active_theme(DEFAULT_THEME)
