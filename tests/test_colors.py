from anonymator.ui.colors import color_for, ENTITY_COLORS


def test_known_types_have_distinct_colors():
    for code in ["PERSON", "ADDRESS", "ORG", "EMAIL", "PHONE", "IBAN"]:
        assert color_for(code).startswith("#")
    assert color_for("PERSON") != color_for("ADDRESS")


def test_unknown_type_falls_back_to_grey():
    assert color_for("ZZZ") == "#8499AB"


def test_login_password_have_colors():
    assert color_for("LOGIN").startswith("#")
    assert color_for("PASSWORD").startswith("#")
    assert color_for("LOGIN") != color_for("PASSWORD")
