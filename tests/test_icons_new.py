import pytest
from anonymator.ui.icons import icon

NEW = ["person", "user", "building", "map-pin", "mail", "phone",
       "credit-card", "scale", "id-card", "globe", "lock", "eye",
       "trash", "palette", "cpu", "github", "package"]

@pytest.mark.parametrize("name", NEW)
def test_new_icon_loads_and_tints(qtbot, name):
    ic = icon(name, "#00965E", size=16)
    assert not ic.isNull()
    assert not ic.pixmap(16, 16).isNull()
