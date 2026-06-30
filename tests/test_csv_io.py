from pathlib import Path
from anonymator.files.csv_io import read_csv, write_csv, sniff_delimiter

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

def test_sniff_ignores_truncated_last_line():
    header = "|".join(f"C{i}" for i in range(18))
    row = "|".join(["x"] * 18)
    text = header + "\n" + "\n".join([row] * 400)   # > 4096 caractères
    sample = text[:4096]                             # coupe la dernière ligne
    assert not sample.endswith("\n")                 # garantit la troncature partielle
    assert sniff_delimiter(sample) == "|"
