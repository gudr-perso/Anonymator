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
    # valid IBAN must be confirmed=True
    good_ents = [e for e in detect_deterministic(f"vir {good}") if e.type == "IBAN"]
    assert good_ents and good_ents[0].confirmed is True
    # invalid IBAN is now emitted confirmed=False (not dropped)
    bad_ents = [e for e in detect_deterministic(f"vir {bad}") if e.type == "IBAN"]
    assert bad_ents and bad_ents[0].confirmed is False


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


def test_invalid_iban_emitted_unconfirmed():
    ents = detect_deterministic("RIB FR76 3000 4000 1200 0000 1234 567")
    iban = [e for e in ents if e.type == "IBAN"]
    assert iban and iban[0].confirmed is False


def test_invalid_nir_emitted_unconfirmed():
    ents = detect_deterministic("ref 2 86 03 69 123 456 78")
    nir = [e for e in ents if e.type == "NIR"]
    assert nir and nir[0].confirmed is False


def test_invalid_bic_still_skipped():
    # "ZZZZZZZZ" a le bon FORMAT BIC mais "ZZ" n'est pas un pays ISO valide :
    # le validateur échoue → BIC n'est pas "unconfirmable", donc rejeté (pas émis).
    ents = detect_deterministic("code ZZZZZZZZ")
    assert not [e for e in ents if e.type == "BIC"]


def test_detects_address_street_line():
    assert ("ADDRESS", "16 RUE JEROME BONAPARTE") in types_at(
        "16 RUE JEROME BONAPARTE")


def test_detects_address_case_insensitive():
    vals = {v for (t, v) in types_at("12 avenue des Champs") if t == "ADDRESS"}
    assert "12 avenue des Champs" in vals


def test_detects_address_with_bis():
    vals = {v for (t, v) in types_at("5 bis rue du Four") if t == "ADDRESS"}
    assert "5 bis rue du Four" in vals


def test_address_stops_at_newline():
    vals = {v for (t, v) in types_at("16 RUE JEROME BONAPARTE\n91300 MASSY")
            if t == "ADDRESS"}
    assert "16 RUE JEROME BONAPARTE" in vals


def test_postal_city_not_matched_as_address():
    assert all(t != "ADDRESS" for (t, v) in types_at("91300 MASSY"))


def test_address_in_prose_does_not_swallow_sentence():
    # En prose (aucun retour à la ligne), la queue de l'adresse ne doit pas
    # engloutir le reste de la phrase. Cf. régression du span géant [ADRESSE].
    text = ("elle a récupéré les clés au 18 rue des Acacias, appt B12 (69003), "
            "puis elle a filé s'installer au calme avant de reprendre le fil.")
    vals = {v for (t, v) in types_at(text) if t == "ADDRESS"}
    assert "18 rue des Acacias" in vals
    # aucune adresse ne doit déborder sur la suite de la phrase
    assert all(len(v) <= len("18 rue des Acacias") for v in vals)


def test_address_stops_at_comma():
    vals = {v for (t, v) in types_at("16 RUE JEROME BONAPARTE, 91300 MASSY")
            if t == "ADDRESS"}
    assert "16 RUE JEROME BONAPARTE" in vals


# --- URL ------------------------------------------------------------------

def test_detects_url_without_scheme():
    """« www.… » sans http:// : c'est la forme usuelle dans un contrat ou un
    pied de page, et le nom de domaine y dit souvent qui est l'organisation."""
    assert ("URL", "www.ateliers-tanguy.net/confidentialite") in types_at(
        "Politique : www.ateliers-tanguy.net/confidentialite")


def test_url_excludes_trailing_punctuation():
    assert ("URL", "https://exemple.fr/a") in types_at(
        "Voir https://exemple.fr/a.")
    assert ("URL", "www.exemple.fr") in types_at("(www.exemple.fr),")


# --- TVA intracommunautaire -------------------------------------------------

def test_detects_vat_fr_with_valid_key():
    # SIREN 404833048 → clé (12 + 3 × (SIREN mod 97)) mod 97 = 83
    ents = [e for e in detect_deterministic("TVA FR83404833048") if e.type == "VAT"]
    assert ents and ents[0].value == "FR83404833048" and ents[0].confirmed


def test_detects_vat_fr_with_spaces():
    assert ("VAT", "FR 83 404 833 048") in types_at("TVA FR 83 404 833 048 fin")


def test_vat_with_wrong_key_but_valid_siren_is_confirmed():
    """Une clé fausse reste un n° de TVA : le format FR + clé + SIREN valide
    est assez spécifique, et c'est l'identifiant de l'entreprise qui fuit."""
    ents = [e for e in detect_deterministic("TVA FR47404833048") if e.type == "VAT"]
    assert ents and ents[0].confirmed


def test_vat_with_invalid_siren_and_key_is_unconfirmed():
    ents = [e for e in detect_deterministic("TVA FR47404833049") if e.type == "VAT"]
    assert ents and ents[0].confirmed is False


# --- SIREN au RCS -----------------------------------------------------------

def test_detects_spaced_siren_after_rcs():
    assert ("SIREN", "404 833 048") in types_at(
        "SARL – RCS Nantes 404 833 048 – TVA")


def test_detects_spaced_siren_after_label():
    assert ("SIREN", "404 833 048") in types_at("SIREN : 404 833 048")


def test_spaced_amount_is_not_a_siren():
    assert all(e.type != "SIREN"
               for e in detect_deterministic("Total 404 833 048 €"))


def test_rcs_siren_with_bad_luhn_is_rejected():
    assert all(e.type != "SIREN"
               for e in detect_deterministic("RCS Nantes 404 833 049"))
