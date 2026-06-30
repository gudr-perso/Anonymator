from datetime import datetime
from anonymator.files import csv_io
from anonymator.files.anonymize_file import scan_csv, apply_csv, anonymize_file
from anonymator.files.columns import default_maskable_columns
from anonymator.referential import Referential
from anonymator.ner import FakeNer


def _doc(tmp_path):
    src = tmp_path / "f.csv"
    src.write_bytes("Nom;Montant\nClaire Martin;100,00\nPaul Durand;50,00\n".encode("cp1252"))
    return csv_io.read_csv(src)


def test_scan_csv_maps_cells_to_entities(tmp_path):
    doc = _doc(tmp_path)
    ref = Referential.load_default()
    ner = FakeNer({"Claire Martin": "PERSON", "Paul Durand": "PERSON"})
    cols = default_maskable_columns(doc.rows, doc.has_header)
    scanned = scan_csv(doc, ner, ref, cols)
    assert (1, 0) in scanned and scanned[(1, 0)][0].type == "PERSON"
    assert (2, 0) in scanned
    assert all(c == 0 for (_r, c) in scanned)


def test_apply_csv_masks_and_reports(tmp_path):
    doc = _doc(tmp_path)
    ref = Referential.load_default()
    ner = FakeNer({"Claire Martin": "PERSON", "Paul Durand": "PERSON"})
    cols = default_maskable_columns(doc.rows, doc.has_header)
    scanned = scan_csv(doc, ner, ref, cols)
    masked_doc, report = apply_csv(doc, scanned, ref)
    assert masked_doc.rows[1][0] == "[PERSONNE]"
    assert masked_doc.rows[2][0] == "[PERSONNE]"
    assert {r["type"] for r in report.to_rows()} == {"PERSON"}


def test_direct_path_keeps_unconfirmed_iban_clear(tmp_path):
    src = tmp_path / "t.txt"
    src.write_text("RIB FR76 3000 4000 1200 0000 1234 567 fin", encoding="utf-8")
    res = anonymize_file(src, FakeNer({}), Referential.load_default(),
                         tmp_path, datetime(2026, 1, 2, 3, 4, 5))
    out = res.output_path.read_text(encoding="utf-8")
    assert "FR76 3000 4000 1200 0000 1234 567" in out   # non confirmé → laissé en clair
    assert "[IBAN]" not in out
