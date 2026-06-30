from anonymator.files.csv_io import sniff_delimiter

def test_sniffs_semicolon():
    sample = "10121000;Libellé;20,00;0,00\n10131000;Autre;2,00;0,00\n"
    assert sniff_delimiter(sample) == ";"

def test_sniffs_pipe():
    sample = "ANC|A nouveaux|1284|20230101|Texte\nANC|A nouveaux|1284|20230102|Autre\n"
    assert sniff_delimiter(sample) == "|"

def test_defaults_to_semicolon_when_ambiguous():
    assert sniff_delimiter("valeur_unique_sans_separateur\n") == ";"
