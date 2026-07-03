from anonymator.files import ooxml


def test_coverage_has_both_lists_nonempty():
    assert set(ooxml.COVERAGE) == {"traite", "non_traite"}
    assert ooxml.COVERAGE["traite"]
    assert ooxml.COVERAGE["non_traite"]
    assert any("OCR" in x or "image" in x for x in ooxml.COVERAGE["non_traite"])
