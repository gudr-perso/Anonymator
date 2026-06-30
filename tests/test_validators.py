from anonymator.validators import luhn_is_valid


def test_luhn_valid_siren():
    assert luhn_is_valid("552081317") is True      # SIREN Danone (valide)


def test_luhn_invalid_siren():
    assert luhn_is_valid("552081318") is False


def test_luhn_rejects_too_short():
    assert luhn_is_valid("7") is False
