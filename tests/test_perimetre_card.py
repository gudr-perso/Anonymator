from anonymator.ui.components.perimetre_card import PerimetreCard
from anonymator.files import ooxml


def test_card_lists_all_coverage_items(qtbot):
    card = PerimetreCard()
    qtbot.addWidget(card)
    text = card.rendered_text()
    for item in ooxml.COVERAGE["traite"]:
        assert item in text
    for item in ooxml.COVERAGE["non_traite"]:
        assert item in text
