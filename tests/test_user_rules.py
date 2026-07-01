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


from pathlib import Path
from anonymator.user_rules import Rule, UserRules


def test_keep_matches_uses_enabled_rules():
    rules = UserRules([Rule("simple", "A#######", "keep", True, "codes internes")])
    assert rules.keep_matches("A0000015")
    assert not rules.keep_matches("bonjour")


def test_disabled_rule_is_inert():
    rules = UserRules([Rule("simple", "A#######", "keep", False, "")])
    assert not rules.keep_matches("A0000015")


def test_mask_rules_exposes_enabled_mask_only():
    rules = UserRules([
        Rule("simple", "PRJ-*", "mask", True, "projets"),
        Rule("simple", "A#######", "keep", True, ""),
        Rule("simple", "OLD-*", "mask", False, ""),
    ])
    got = [r.pattern for r, _ in rules.mask_rules()]
    assert got == ["PRJ-*"]


def test_invalid_regex_rule_is_collected_not_crashing():
    rules = UserRules([Rule("regex", "A(\\d{7}", "keep", True, "")])
    assert rules.keep_matches("A0000015") is False
    assert len(rules.invalid) == 1


def test_load_absent_file_migrates_fallback_terms(tmp_path):
    path = tmp_path / "user_rules.json"
    rules = UserRules.load(path, fallback_terms=["service client", "banque"])
    assert path.exists()                       # migration écrite
    assert rules.keep_matches("service client")
    assert rules.keep_matches("banque")
    assert all(r.action == "keep" and r.mode == "simple" for r in rules.rules)


def test_load_existing_file_ignores_fallback(tmp_path):
    path = tmp_path / "user_rules.json"
    UserRules([Rule("simple", "PRJ-*", "mask", True, "")]).save(path)
    rules = UserRules.load(path, fallback_terms=["service client"])
    assert not rules.keep_matches("service client")
    assert [r.pattern for r, _ in rules.mask_rules()] == ["PRJ-*"]


def test_save_then_load_roundtrip(tmp_path):
    path = tmp_path / "user_rules.json"
    original = UserRules([Rule("regex", r"A\d{7}", "keep", True, "note")])
    original.save(path)
    reloaded = UserRules.load(path)
    assert reloaded.keep_matches("A0000015")
