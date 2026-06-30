from anonymator.secrets_detect import detect_secrets


def _by_type(text):
    out = {}
    for e in detect_secrets(text):
        out.setdefault(e.type, []).append(e.value)
    return out


def test_password_keyword():
    r = _by_type("son mot de passe provisoire — V3lo!2026#Claire — en se disant")
    assert "V3lo!2026#Claire" in r.get("PASSWORD", [])


def test_login_keyword_parenthesis():
    r = _by_type("un accès au compte (h.dupont90), mot de passe")
    assert "h.dupont90" in r.get("LOGIN", [])


def test_login_connecte_avec():
    r = _by_type("elle s'était connectée la veille avec claire.martin86.")
    assert "claire.martin86" in r.get("LOGIN", [])


def test_offsets_point_to_value():
    text = "mot de passe : T0ulouse*Hugo-90 ok"
    e = next(e for e in detect_secrets(text) if e.type == "PASSWORD")
    assert text[e.start:e.end] == "T0ulouse*Hugo-90"


def test_password_keyword_not_inside_word():
    # "impasse" / "bypass" contiennent "passe"/"pass" mais ne sont PAS un mot-clé
    assert all(e.type != "PASSWORD" for e in detect_secrets("dans une impasse : Toulouse"))
    assert all(e.type != "PASSWORD" for e in detect_secrets("un bypass : reseau"))


def test_token_strips_trailing_colon():
    # un ':' final ne doit pas rester collé à la valeur
    e = next(e for e in detect_secrets("mot de passe : Secret123: suite") if e.type == "PASSWORD")
    assert e.value == "Secret123"


def test_login_avec_is_bounded():
    # 'avec' très loin du verbe 'connecté' ne doit pas capturer un nom de collaborateur
    text = "il est connecté au reseau et il travaille tres souvent depuis des annees avec Jean"
    assert all(e.type != "LOGIN" for e in detect_secrets(text))


def test_entropy_detects_strong_token():
    r = _by_type("cle V3lo!2026#Claire ailleurs")
    assert "V3lo!2026#Claire" in r.get("PASSWORD", [])


def test_entropy_ignores_account_number():
    assert all(e.type != "PASSWORD" for e in detect_secrets("compte 41100000 montant"))


def test_entropy_ignores_plain_words():
    assert all(e.type != "PASSWORD" for e in detect_secrets("Bonjour Madame Toulouse"))


def test_entropy_no_duplicate_with_contextual():
    # un secret déjà capturé par la règle contextuelle ne doit pas être émis deux fois
    ents = [e for e in detect_secrets("mot de passe : T0ulouse*Hugo-90 fin") if e.type == "PASSWORD"]
    vals = [e.value for e in ents]
    assert vals.count("T0ulouse*Hugo-90") == 1


def test_login_keyword_not_followed_by_plain_word():
    # "identifiant administratif" : 'administratif' est un mot ordinaire, pas un identifiant
    assert all(e.value != "administratif" for e in detect_secrets("identifiant administratif 12345"))


def test_password_keyword_not_followed_by_plain_word():
    # "mot de passe oublié" : 'oublié' n'est pas un mot de passe
    assert all(e.type != "PASSWORD" or e.value != "oublié"
               for e in detect_secrets("mot de passe oublié hier"))
