from pathlib import Path
from anonymator.files.csv_io import read_csv, write_csv

def test_roundtrip_preserves_rows_delimiter_encoding(tmp_path):
    src = tmp_path / "in.csv"
    src.write_bytes("10131000;CS appelé;2,00\n51211000;Banque CRCA;9702,88\n"
                    .encode("cp1252"))
    doc = read_csv(src)
    assert doc.delimiter == ";"
    assert doc.encoding == "cp1252"
    assert doc.rows[0] == ["10131000", "CS appelé", "2,00"]
    out = tmp_path / "out.csv"
    write_csv(doc, out)
    assert read_csv(out).rows == doc.rows
    assert out.read_bytes().decode("cp1252").count(";") == 4

def test_read_detects_header(tmp_path):
    src = tmp_path / "h.csv"
    src.write_bytes("JournalCode|JournalLib|Debit\nANC|A nouveaux|0,00\n"
                    .encode("utf-8"))
    doc = read_csv(src)
    assert doc.delimiter == "|"
    assert doc.has_header is True
