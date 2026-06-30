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
