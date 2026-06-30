from anonymator.files.encoding import detect_encoding

def test_detects_utf8():
    assert detect_encoding("Société".encode("utf-8")) == "utf-8"

def test_falls_back_to_cp1252_for_latin1_bytes():
    assert detect_encoding("Société".encode("cp1252")) == "cp1252"

def test_pure_ascii_is_utf8():
    assert detect_encoding(b"Banque Credit Agricole") == "utf-8"
