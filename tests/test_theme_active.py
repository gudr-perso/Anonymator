from anonymator.ui.theme import set_active_theme, DEFAULT_THEME
from anonymator.ui.components.grid import grid_colors


def test_grid_colors_follow_active_theme():
    try:
        set_active_theme("cuma")
        assert grid_colors() == ("#E8F3EA", "#E1EBE3")
        set_active_theme("cap")
        assert grid_colors() == ("#0a1556", "#1e2a63")
    finally:
        set_active_theme(DEFAULT_THEME)
