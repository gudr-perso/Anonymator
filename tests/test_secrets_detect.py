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
