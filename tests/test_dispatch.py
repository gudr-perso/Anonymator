from datetime import datetime
import pytest
from anonymator.referential import Referential
from anonymator.ner import FakeNer
from anonymator.files.anonymize_file import anonymize_file, UnsupportedFormat

def test_dispatches_by_extension(tmp_path):
    src = tmp_path / "n.txt"
    src.write_bytes("Claire Martin".encode("cp1252"))
    ref = Referential.load_default(); ner = FakeNer({"Claire Martin": "PERSON"})
    res = anonymize_file(src, ner, ref, tmp_path, when=datetime(2026, 1, 1))
    assert res.output_path.suffix == ".txt"

def test_rejects_pdf(tmp_path):
    src = tmp_path / "doc.pdf"
    src.write_bytes(b"%PDF-1.7")
    ref = Referential.load_default(); ner = FakeNer({})
    with pytest.raises(UnsupportedFormat) as exc:
        anonymize_file(src, ner, ref, tmp_path, when=datetime(2026, 1, 1))
    assert ".pdf" in str(exc.value).lower()

def test_xlsx_with_column_override_not_supported(tmp_path):
    import openpyxl
    src = tmp_path / "b.xlsx"
    openpyxl.Workbook().save(src)
    ref = Referential.load_default(); ner = FakeNer({})
    with pytest.raises(NotImplementedError):
        anonymize_file(src, ner, ref, tmp_path,
                       when=datetime(2026, 1, 1), exclude={1})
