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


def _fec(tmp_path):
    src = tmp_path / "404833048FEC20251231.txt"
    lines = ["JournalCode\tJournalLib\tCompAuxLib\tDebit",
             "VE\tJournal des ventes\tClaire Martin\t10,00",
             "VE\tJournal des ventes\tClaire Martin\t0,00"]
    src.write_bytes("\r\n".join(lines).encode("cp1252") + b"\r\n")
    return src, lines


def test_tabular_txt_is_routed_as_a_table(tmp_path):
    """Un FEC est un .txt à tabulations : il relève du traitement par
    colonnes, pas du texte libre."""
    from anonymator.files.anonymize_file import is_tabular
    src, _ = _fec(tmp_path)
    assert is_tabular(src)
    prose = tmp_path / "note.txt"
    prose.write_text("Bonjour Claire,\nvoici la note.\n", encoding="utf-8")
    assert not is_tabular(prose)


def test_tabular_txt_keeps_its_structure(tmp_path, monkeypatch):
    from anonymator.files import anonymize_file as af
    called = []
    real = af.anonymize_csv
    monkeypatch.setattr(af, "anonymize_csv",
                        lambda *a, **k: called.append(1) or real(*a, **k))
    src, lines = _fec(tmp_path)
    out_dir = tmp_path / "out"; out_dir.mkdir()
    ref = Referential.load_default(); ner = FakeNer({"Claire Martin": "PERSON"})
    res = af.anonymize_file(src, ner, ref, out_dir, when=datetime(2026, 1, 1))
    assert called
    out = res.output_path.read_bytes().decode("cp1252")
    assert res.output_path.suffix == ".txt"
    assert out.splitlines()[0] == lines[0]
    assert "Claire Martin" not in out
    assert all(line.count("\t") == 3 for line in out.splitlines())
