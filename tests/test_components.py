from PySide6.QtGui import QIcon
from anonymator.ui.icons import icon, ICON_NAMES

def test_icons_load(qtbot):
    for name in ICON_NAMES:
        ic = icon(name)
        assert isinstance(ic, QIcon)
        assert not ic.isNull()
