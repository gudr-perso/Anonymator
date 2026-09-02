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


def test_quoted_delimiter_does_not_break_detection():
    """Un champ entre guillemets a le droit de contenir le séparateur. Compter
    les séparateurs dans la ligne brute faisait échouer la consistance, d'où un
    repli sur « ; » et un fichier relu — puis réécrit — en une seule colonne."""
    sample = ('nom,adresse,ville\n'
              '"Dupont, Jean","12 rue A",Nantes\n'
              'Martin,3 rue B,Rennes\n')
    assert sniff_delimiter(sample) == ","


def test_quoted_semicolon_keeps_semicolon():
    sample = ('nom;adresse;ville\n'
              'Dupont;"12 rue A; bat B";Nantes\n'
              'Martin;3 rue B;Rennes\n')
    assert sniff_delimiter(sample) == ";"


def test_majority_wins_when_a_line_is_irregular():
    """Échantillon tronqué au milieu d'un champ cité : les lignes ne s'accordent
    plus toutes, mais « ; » reste le bon séparateur pour l'essentiel du fichier."""
    sample = 'a;b;c\nd;e;f\n"g;h\ni;j;k\n'
    assert sniff_delimiter(sample) == ";"
