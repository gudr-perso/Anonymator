from anonymator.ui.theme import THEME_LABELS, label_for_theme, theme_for_label, THEMES

def test_every_theme_has_label():
    for key in THEMES:
        assert key in THEME_LABELS

def test_roundtrip():
    for key in THEMES:
        assert theme_for_label(label_for_theme(key)) == key

def test_cuma_label():
    assert label_for_theme("cuma") == "CUMA — vert identitaire"
