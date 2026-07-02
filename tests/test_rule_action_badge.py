from anonymator.ui.components.rule_action_badge import RuleActionBadge


def test_keep_is_green_eye(qtbot):
    b = RuleActionBadge("keep")
    qtbot.addWidget(b)
    assert "Ne jamais masquer" in b.text()
    assert "00965E" in b.styleSheet().upper() or "31B700" in b.styleSheet().upper()


def test_mask_is_orange(qtbot):
    b = RuleActionBadge("mask")
    qtbot.addWidget(b)
    assert "Toujours masquer" in b.text()
    assert "E8621A" in b.styleSheet().upper()
