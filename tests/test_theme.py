from anonymator.ui.theme import THEMES, build_qss, DEFAULT_THEME


def test_two_themes_with_required_tokens():
    assert set(THEMES) == {"cuma", "cap"}
    for tokens in THEMES.values():
        for key in ["primary", "action", "dark", "accent", "bg", "text"]:
            assert tokens[key].startswith("#")


def test_default_theme_is_cuma():
    assert DEFAULT_THEME == "cuma"


def test_build_qss_injects_theme_colors():
    qss = build_qss("cap")
    assert THEMES["cap"]["action"] in qss
    assert "QPushButton" in qss


def test_build_qss_unknown_theme_falls_back_to_default():
    assert build_qss("zzz") == build_qss(DEFAULT_THEME)
