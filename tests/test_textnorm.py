from anonymator.textnorm import normalize


def test_normalize_lowercases_and_strips_accents():
    assert normalize("Crédit Agricole") == "credit agricole"
    assert normalize("  SERVICE   Client ") == "service client"
