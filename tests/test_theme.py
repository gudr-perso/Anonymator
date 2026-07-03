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


def test_cuma_tokens_are_frozen():
    """Garde-fou : CUMA ne doit jamais bouger (rendu identique au pixel)."""
    from anonymator.ui.theme import THEMES
    assert THEMES["cuma"] == {
        "primary": "#31B700", "action": "#00965E", "dark": "#063b27",
        "accent": "#E8621A", "accent_hover": "#C9500F", "bg": "#FFFFFF",
        "text": "#10331F", "bg_hero": "#E8F3EA", "surface": "#FFFFFF",
        "surface_alt": "#F3FAF4", "border": "#E2E8E4", "text_muted": "#6B7C72",
        "info": "#4FA8D8", "info_hover": "#3D93C2",
        "grid_bg": "#E8F3EA", "grid_line": "#E1EBE3",
        "hero_text": "#10331F", "hero_muted": "#6B7C72",
        "toggle_off": "#C7D2CC", "logo": "logo.png",
        "header_tag": "RÉSEAU CUMA",
    }


def test_cap_header_tag_is_empty():
    from anonymator.ui.theme import THEMES
    assert THEMES["cap"]["header_tag"] == ""
    assert THEMES["cuma"]["header_tag"] == "RÉSEAU CUMA"


def test_cap_has_same_keys_as_cuma():
    from anonymator.ui.theme import THEMES
    assert set(THEMES["cap"]) == set(THEMES["cuma"])


def test_active_theme_getset():
    from anonymator.ui.theme import (
        set_active_theme, active_theme, DEFAULT_THEME)
    try:
        set_active_theme("cap")
        assert active_theme() == "cap"
        set_active_theme("inconnu")          # retombe sur le défaut
        assert active_theme() == DEFAULT_THEME
    finally:
        set_active_theme(DEFAULT_THEME)


def test_color_reads_active_theme():
    from anonymator.ui.theme import set_active_theme, color, DEFAULT_THEME
    try:
        set_active_theme("cap")
        assert color("action") == "#138fdb"
        assert color("grid_bg") == "#0a1556"
        assert color("action", "cuma") == "#00965E"   # override explicite
    finally:
        set_active_theme(DEFAULT_THEME)



def test_pageinfo_uses_hero_text_readable_on_grid():
    """Le libellé de pagination est posé sur le fond quadrillé (transparent) :
    il doit suivre hero_text (blanc en CAP sur navy) et rester inchangé en CUMA."""
    from anonymator.ui.theme import build_qss
    assert "QLabel#pageInfo { color: #FFFFFF" in build_qss("cap")
    assert "QLabel#pageInfo { color: #10331F" in build_qss("cuma")
