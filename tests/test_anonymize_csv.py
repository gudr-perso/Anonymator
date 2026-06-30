from datetime import datetime
from pathlib import Path
from anonymator.referential import Referential
from anonymator.ner import FakeNer
from anonymator.files.anonymize_file import anonymize_csv

def test_masks_text_columns_writes_new_file_and_report(tmp_path):
    src = tmp_path / "fec.csv"
    src.write_bytes(
        ("CompteNum;CompAuxLib;Debit\n"
         "41100000;Claire Martin;100,00\n"
         "41100000;Claire Martin;50,00\n").encode("cp1252"))
    ref = Referential.load_default()
    ner = FakeNer({"Claire Martin": "PERSON"})
    result = anonymize_csv(src, ner, ref, tmp_path,
                           when=datetime(2026, 6, 24, 17, 18, 0))
    assert result.output_path.name == "fec_ano_20260624171800.csv"
    assert src.read_bytes().decode("cp1252").count("Claire Martin") == 2
    out_text = result.output_path.read_bytes().decode("cp1252")
    assert "Claire Martin" not in out_text
    assert out_text.count("[PERSONNE]") == 2
    assert "41100000" in out_text and "100,00" in out_text
    rows = result.report.to_rows()
    person = next(r for r in rows if r["original"] == "Claire Martin")
    assert person["occurrences"] == 2

def test_column_overrides_exclude(tmp_path):
    src = tmp_path / "x.csv"
    src.write_bytes("Nom;Note\nClaire Martin;RAS Claire Martin\n".encode("cp1252"))
    ref = Referential.load_default()
    ner = FakeNer({"Claire Martin": "PERSON"})
    result = anonymize_csv(src, ner, ref, tmp_path,
                           when=datetime(2026, 1, 1, 0, 0, 0), exclude={1})
    out = result.output_path.read_bytes().decode("cp1252")
    assert out == "Nom;Note\n[PERSONNE];RAS Claire Martin\n"
