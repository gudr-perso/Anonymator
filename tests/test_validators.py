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


def test_luhn_valid_real_sirens():
    # vrais SIREN valides qui échouaient sous la version buguée (parité inversée)
    assert luhn_is_valid("542107651") is True   # BNP Paribas
    assert luhn_is_valid("775672272") is True   # EDF


def test_luhn_detects_single_digit_error():
    assert luhn_is_valid("542107652") is False  # un chiffre changé → invalide


from anonymator.validators import bic_is_plausible, postal_code_fr_is_plausible


def test_bic_plausible_8_and_11():
    assert bic_is_plausible("BNPAFRPP") is True       # 8 chars
    assert bic_is_plausible("BNPAFRPPXXX") is True     # 11 chars (branche)


def test_bic_rejects_unknown_country():
    # "VIREMENT" : pays "ME" est ISO valide -> on ne peut pas l'exclure ; mais
    # "FACTURES" -> pays "UR" inexistant -> rejeté
    assert bic_is_plausible("FACTURES") is False


def test_bic_rejects_bad_shape():
    assert bic_is_plausible("ABC123") is False


def test_postal_plausible():
    assert postal_code_fr_is_plausible("75008") is True
    assert postal_code_fr_is_plausible("20000") is True   # Corse
    assert postal_code_fr_is_plausible("00123") is False   # dept 00
    assert postal_code_fr_is_plausible("1234") is False    # pas 5 chiffres
