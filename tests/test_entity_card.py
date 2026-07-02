from anonymator.ui.components.entity_card import EntityCard


def test_reflects_initial_state(qtbot):
    card = EntityCard("PERSON", active=True)
    qtbot.addWidget(card)
    assert card.toggle.isChecked() is True


def test_emits_on_toggle(qtbot):
    seen = []
    card = EntityCard("EMAIL", active=False)
    qtbot.addWidget(card)
    card.toggled.connect(lambda code, on: seen.append((code, on)))
    card.toggle.setChecked(True)
    assert seen == [("EMAIL", True)]
