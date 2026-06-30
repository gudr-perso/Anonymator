from anonymator.files.csv_io import sniff_delimiter

def test_sniffs_semicolon():
    sample = "10121000;Libellé;20,00;0,00\n10131000;Autre;2,00;0,00\n"
    assert sniff_delimiter(sample) == ";"

def test_sniffs_pipe():
    sample = "ANC|A nouveaux|1284|20230101|Texte\nANC|A nouveaux|1284|20230102|Autre\n"
    assert sniff_delimiter(sample) == "|"

def test_defaults_to_semicolon_when_ambiguous():
    assert sniff_delimiter("valeur_unique_sans_separateur\n") == ";"

def test_prefers_semicolon_over_decimal_commas():
    # GL FR : 1 point-virgule délimiteur, 3 virgules décimales par ligne
    sample = "x;12,00;34,50;56,00\ny;1,00;2,00;3,00\n"
    assert sniff_delimiter(sample) == ";"

def test_genuine_comma_csv_still_detected():
    assert sniff_delimiter("a,b,c\n1,2,3\n") == ","
