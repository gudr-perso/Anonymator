from datetime import datetime
from pathlib import Path
from anonymator.output_naming import anonymized_path

def test_builds_suffixed_name_in_output_dir():
    src = Path("C:/data/balance_2026.csv")
    out = anonymized_path(src, Path("D:/sorties"), datetime(2026, 6, 24, 17, 18, 0))
    assert out == Path("D:/sorties/balance_2026_ano_20260624171800.csv")

def test_preserves_multidot_stem_and_extension():
    src = Path("/x/616870200FEC20231231.csv")
    out = anonymized_path(src, Path("/out"), datetime(2026, 1, 2, 3, 4, 5))
    assert out.name == "616870200FEC20231231_ano_20260102030405.csv"
