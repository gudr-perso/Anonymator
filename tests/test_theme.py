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


def test_themes_have_extended_tokens():
    from anonymator.ui.theme import THEMES
    for tokens in THEMES.values():
        for key in ["bg", "bg_hero", "surface", "surface_alt", "border",
                    "primary", "action", "accent", "text", "text_muted"]:
            assert key in tokens and tokens[key].startswith("#")


def test_qss_includes_card_and_header_styles():
    from anonymator.ui.theme import build_qss
    qss = build_qss("cuma")
    assert "#Card" in qss
    assert "HeaderBand" in qss
