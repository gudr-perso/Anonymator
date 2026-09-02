from anonymator.files.encoding import detect_encoding

def test_detects_utf8():
    assert detect_encoding("Société".encode("utf-8")) == "utf-8"

def test_falls_back_to_cp1252_for_latin1_bytes():
    assert detect_encoding("Société".encode("cp1252")) == "cp1252"

def test_pure_ascii_is_utf8():
    assert detect_encoding(b"Banque Credit Agricole") == "utf-8"


def test_never_returns_an_encoding_that_cannot_decode():
    """0x81 n'est pas défini en cp1252 : renvoyer « cp1252 » sans vérifier
    faisait lever un UnicodeDecodeError chez l'appelant."""
    data = "nom;ville\nDupont;Nantes".encode("cp1252") + b"\x81\n"
    enc = detect_encoding(data)
    assert data.decode(enc)          # ne doit pas lever


def test_undecodable_bytes_fall_back_to_latin1():
    assert detect_encoding(b"\x81\x8d\x90") == "latin-1"
