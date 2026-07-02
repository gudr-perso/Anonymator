from anonymator.ui.components.rule_action_badge import RuleActionBadge


def test_keep_is_green_eye(qtbot):
    b = RuleActionBadge("keep")
    qtbot.addWidget(b)
    assert b.text() == "Ne jamais masquer"
    assert b.color.upper() == "#00965E"


def test_mask_is_orange(qtbot):
    b = RuleActionBadge("mask")
    qtbot.addWidget(b)
    assert b.text() == "Toujours masquer"
    assert b.color.upper() == "#E8621A"


def test_badge_has_positive_size(qtbot):
    """La pastille icône+texte doit avoir une largeur mesurée réaliste
    (garde-fou contre le rognage constaté avec les emoji)."""
    b = RuleActionBadge("keep")
    qtbot.addWidget(b)
    assert b.sizeHint().width() > 80
