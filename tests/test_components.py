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
