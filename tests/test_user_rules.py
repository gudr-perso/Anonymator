from anonymator.user_rules import compile_pattern


def test_simple_hash_is_digit():
    pat = compile_pattern("simple", "A#######")
    assert pat.fullmatch("A0000015")
    assert not pat.fullmatch("A000001")     # 6 chiffres
    assert not pat.fullmatch("XA0000015")   # ancré (fullmatch)


def test_simple_star_is_anything():
    pat = compile_pattern("simple", "FACT.*")
    assert pat.fullmatch("FACT.01/01/2023")
    assert pat.fullmatch("FACT.")
    assert not pat.fullmatch("XFACT.2023")


def test_simple_question_is_one_char():
    pat = compile_pattern("simple", "REF-?")
    assert pat.fullmatch("REF-9")
    assert not pat.fullmatch("REF-99")


def test_simple_escapes_special_chars():
    # le '.' d'un motif simple est littéral, pas un joker regex
    pat = compile_pattern("simple", "A.N. au")
    assert pat.fullmatch("A.N. au")
    assert not pat.fullmatch("AXNX au")


def test_simple_is_case_insensitive():
    pat = compile_pattern("simple", "fact.*")
    assert pat.fullmatch("FACT.2023")


def test_regex_mode_passthrough():
    pat = compile_pattern("regex", r"A\d{7}")
    assert pat.fullmatch("A0000015")
    assert not pat.fullmatch("A00000")


def test_invalid_regex_returns_none():
    assert compile_pattern("regex", "A(\\d{7}") is None
