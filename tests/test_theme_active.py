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


def test_home_logo_filename_follows_theme():
    from anonymator.ui.theme import color, set_active_theme, DEFAULT_THEME
    try:
        set_active_theme("cuma")
        assert color("logo") == "logo.png"
        set_active_theme("cap")
        # thème CAP figé sur l'icône générique de l'app (cf. release v0.4.0,
        # qui a remplacé le logo CAP Consulting par logo-app.png)
        assert color("logo") == "logo-app.png"
    finally:
        set_active_theme(DEFAULT_THEME)


def test_home_screen_builds_under_cap(qtbot):
    from anonymator.ui.theme import set_active_theme, DEFAULT_THEME
    from anonymator.ui.home_screen import HomeScreen
    try:
        set_active_theme("cap")
        s = HomeScreen(lambda: None, lambda: None, lambda: None)
        qtbot.addWidget(s)
        assert s is not None
    finally:
        set_active_theme(DEFAULT_THEME)
