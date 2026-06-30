from anonymator.files.columns import looks_structured, default_maskable_columns


def test_looks_structured_true_for_numbers_dates_empty():
    assert looks_structured("       1284")
    assert looks_structured("15866,00")
    assert looks_structured("20230101")
    assert looks_structured("")
    assert looks_structured("51211000")


def test_looks_structured_false_when_has_letter():
    assert not looks_structured("Banque Crédit Agricole")
    assert not looks_structured("A.N. au 01/01/2023")


def test_default_maskable_columns_skips_header_and_numeric_cols():
    rows = [
        ["CompteNum", "CompteLib", "Debit"],
        ["10131000", "CS appelé", "0,00"],
        ["51211000", "Banque CRCA", "9702,88"],
    ]
    cols = default_maskable_columns(rows, has_header=True)
    assert cols == {1}


def test_default_maskable_columns_without_header():
    rows = [["10121000", "CS appelé", "20,00"], ["16423000", "", "2173,39"]]
    assert default_maskable_columns(rows, has_header=False) == {1}
