from anonymator.deterministic import detect_deterministic


def types_at(text):
    return {(e.type, e.value) for e in detect_deterministic(text)}


def test_detects_email():
    assert ("EMAIL", "jp.lefevre@gmail.com") in types_at(
        "Contact : jp.lefevre@gmail.com.")


def test_detects_phone_fr():
    assert ("PHONE", "06 12 34 56 78") in types_at("Tel 06 12 34 56 78")


def test_detects_iban_only_if_valid_checksum():
    good = "FR7630006000011234567890189"
    bad = "FR7630006000011234567890188"
    assert ("IBAN", good) in types_at(f"vir {good}")
    assert all(e.type != "IBAN" for e in detect_deterministic(f"vir {bad}"))


def test_detects_siret_via_luhn():
    assert ("SIRET", "73282932000074") in types_at("SIRET 73282932000074")


def test_spans_are_correct():
    text = "mail jp.lefevre@gmail.com fin"
    e = next(e for e in detect_deterministic(text) if e.type == "EMAIL")
    assert text[e.start:e.end] == "jp.lefevre@gmail.com"
    assert e.source == "deterministic"


def test_detects_bic():
    assert ("BIC", "BNPAFRPPXXX") in types_at("Virement BIC BNPAFRPPXXX vers...")
    assert ("BIC", "SOGEFRPP") in types_at("ref SOGEFRPP fin")


def test_detects_postal_code_fr():
    assert ("POSTAL_CODE", "75008") in types_at("Paris 75008 France")


def test_rejects_implausible_postal_code():
    assert all(e.type != "POSTAL_CODE"
               for e in detect_deterministic("ref 00123 xx"))
