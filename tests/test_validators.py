from anonymator.validators import luhn_is_valid, iban_is_valid, nir_is_valid


def test_luhn_valid_siren():
    assert luhn_is_valid("552081317") is True      # SIREN Danone (valide)


def test_luhn_invalid_siren():
    assert luhn_is_valid("552081318") is False


def test_luhn_rejects_too_short():
    assert luhn_is_valid("7") is False


def test_iban_valid_fr():
    assert iban_is_valid("FR7630006000011234567890189") is True


def test_iban_valid_with_spaces():
    assert iban_is_valid("FR76 3000 6000 0112 3456 7890 189") is True


def test_iban_invalid_checksum():
    assert iban_is_valid("FR7630006000011234567890188") is False


# NIR keys computed: key = 97 - (int(body_with_substitution) % 97)
# Standard body 1550813084024 → key 17
# Corsica 2A body 155082A084024 → substituted 1550819084024 → key 49
def test_nir_valid():
    assert nir_is_valid("1 55 08 13 084 024 17") is True


def test_nir_invalid_key():
    assert nir_is_valid("1 55 08 13 084 024 18") is False


def test_nir_corsica_2a():
    assert nir_is_valid("1 55 08 2A 084 024 49") is True
