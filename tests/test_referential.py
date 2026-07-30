from anonymator.referential import Referential

def test_loads_default_referential():
    ref = Referential.load_default()
    assert ref.tag_for("EMAIL") == "[EMAIL]"
    assert ref.is_active("EMAIL") is True
    assert ref.is_active("URL") is False

def test_active_ner_labels_maps_codes_to_french_labels():
    ref = Referential.load_default()
    assert set(ref.active_ner_labels()) == {"personne", "adresse postale", "organisation"}

def test_active_deterministic_types_excludes_inactive():
    ref = Referential.load_default()
    types = ref.active_deterministic_types()
    assert "EMAIL" in types and "URL" not in types

def test_bic_and_postal_code_are_opt_in_by_default():
    # bruyants sur les fichiers comptables → désactivés par défaut, activables à la demande
    ref = Referential.load_default()
    assert ref.is_active("BIC") is False
    assert ref.is_active("POSTAL_CODE") is False
    types = ref.active_deterministic_types()
    assert "BIC" not in types and "POSTAL_CODE" not in types


def test_login_and_password_active_by_default():
    ref = Referential.load_default()
    assert ref.is_active("LOGIN") is True
    assert ref.is_active("PASSWORD") is True

def test_bic_cp_url_inactive_by_default():
    ref = Referential.load_default()
    assert ref.is_active("BIC") is False
    assert ref.is_active("POSTAL_CODE") is False
    assert ref.is_active("URL") is False


def test_override_enables_inactive_type():
    ref = Referential.load_default(overrides={"BIC": True})
    assert ref.is_active("BIC") is True


def test_override_disables_active_type():
    ref = Referential.load_default(overrides={"PERSON": False})
    assert ref.is_active("PERSON") is False


def test_default_stoplist_loaded():
    ref = Referential.load_default()
    assert "service client" in ref.ner_stoplist()   # normalisé


def test_sensitivity_for():
    ref = Referential.load_default()
    assert ref.sensitivity_for("PERSON") == "Haute"
    assert ref.sensitivity_for("POSTAL_CODE") == "Basse"
    assert ref.sensitivity_for("INCONNU") == "Basse"


from anonymator.user_rules import UserRules, Rule


def test_regle_interne_tag_resolves():
    ref = Referential.load_default()
    assert ref.tag_for("REGLE_INTERNE") == "[REGLE-INTERNE]"


def test_regle_interne_not_in_ner_or_deterministic():
    ref = Referential.load_default()
    assert "REGLE_INTERNE" not in ref.active_deterministic_types()
    assert set(ref.active_ner_labels()) == {"personne", "adresse postale", "organisation"}


def test_default_seeds_user_rules_from_stoplist():
    ref = Referential.load_default()
    assert ref.user_rules.keep_matches("service client")


def test_with_user_rules_replaces_ruleset():
    ref = Referential.load_default().with_user_rules(
        UserRules([Rule("simple", "PRJ-*", "mask", True, "")]))
    assert not ref.user_rules.keep_matches("service client")
    assert [r.pattern for r, _ in ref.user_rules.mask_rules()] == ["PRJ-*"]


def test_active_codes_lists_only_active_types():
    """La détection automatique ne retient que les types actifs."""
    ref = Referential.load_default()
    codes = ref.active_codes()
    assert "PERSON" in codes and "PHONE" in codes
    assert "POSTAL_CODE" not in codes and "BIC" not in codes and "URL" not in codes


def test_mask_pseudo_type_is_defined_and_inactive():
    """Type neutre pour le masquage manuel d'une colonne sans type sémantique.
    Inactif : il ne doit jamais sortir de la détection automatique."""
    ref = Referential.load_default()
    assert ref.tag_for("MASK") == "[MASQUÉ]"
    assert ref.is_active("MASK") is False
    assert "MASK" not in ref.active_codes()


def test_forceable_codes_include_inactive_but_not_the_neutral_mask():
    """Le forçage manuel étant explicite, il propose tous les vrais types, y
    compris les inactifs. Le pseudo-type neutre MASK est présenté à part."""
    ref = Referential.load_default()
    codes = ref.forceable_codes()
    assert "PERSON" in codes            # actif
    assert "POSTAL_CODE" in codes       # inactif, forçable
    assert "MASK" not in codes          # neutre, ajouté séparément par l'UI


def test_active_codes_follows_overrides():
    ref = Referential.load_default(overrides={"PERSON": False, "URL": True})
    codes = ref.active_codes()
    assert "PERSON" not in codes and "URL" in codes
