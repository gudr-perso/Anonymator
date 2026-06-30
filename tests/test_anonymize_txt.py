from datetime import datetime
from anonymator.referential import Referential
from anonymator.ner import FakeNer
from anonymator.files.anonymize_file import anonymize_txt

def test_masks_whole_text_file(tmp_path):
    src = tmp_path / "note.txt"
    src.write_bytes("Contact Claire Martin au 06 12 34 56 78.".encode("cp1252"))
    ref = Referential.load_default()
    ner = FakeNer({"Claire Martin": "PERSON"})
    res = anonymize_txt(src, ner, ref, tmp_path,
                        when=datetime(2026, 6, 24, 17, 18, 0))
    out = res.output_path.read_bytes().decode("cp1252")
    assert out == "Contact [PERSONNE] au [TEL]."
    assert res.output_path.name == "note_ano_20260624171800.txt"
    assert {r["type"] for r in res.report.to_rows()} == {"PERSON", "PHONE"}
