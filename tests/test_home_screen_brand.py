from PySide6.QtWidgets import QLabel
from anonymator.brand import lock_brand, reset_brand
from anonymator.ui.theme import set_active_theme, DEFAULT_THEME
from anonymator.ui import home_screen
from anonymator.ui.home_screen import HomeScreen


def teardown_function():
    reset_brand()
    set_active_theme(DEFAULT_THEME)


def _label_texts(widget):
    return [c.text() for c in widget.findChildren(QLabel)]


def test_hero_text_fallback_uses_brand_name_not_hardcoded_cuma(qtbot, tmp_path, monkeypatch):
    """Quand l'asset logo est absent, le héros bascule sur un repli texte.
    Ce repli doit afficher le nom de la marque active — jamais « CUMA » en dur,
    ce qui fuiterait la marque adverse dans un build CAP."""
    # Simule un build CAP verrouillé…
    set_active_theme("cap")
    lock_brand("cap")
    # …dont le dossier d'assets ne contient aucun logo → force la branche de repli.
    monkeypatch.setattr(home_screen, "_ASSETS", tmp_path)

    s = HomeScreen(lambda: None, lambda: None, lambda: None)
    qtbot.addWidget(s)

    texts = _label_texts(s)
    assert "CUMA" not in texts            # plus de « CUMA » codé en dur
    assert "CAP'nonyme" in texts          # le repli suit la marque active
