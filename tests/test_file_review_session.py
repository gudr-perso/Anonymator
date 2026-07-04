from anonymator.files import csv_io
from anonymator.files.anonymize_file import scan_csv
from anonymator.files.columns import default_maskable_columns
from anonymator.referential import Referential
from anonymator.ner import FakeNer
from anonymator.core.file_review_session import FileReviewSession


def _session(tmp_path):
    src = tmp_path / "f.csv"
    src.write_bytes(
        "Nom;Montant\nClaire Martin;100,00\nClaire Martin;50,00\nPaul Durand;7,00\n"
        .encode("cp1252"))
    doc = csv_io.read_csv(src)
    ref = Referential.load_default()
    ner = FakeNer({"Claire Martin": "PERSON", "Paul Durand": "PERSON"})
    cols = default_maskable_columns(doc.rows, doc.has_header)
    scanned = scan_csv(doc, ner, ref, cols)
    return FileReviewSession(doc, scanned, ref, cols)


def test_types_and_values(tmp_path):
    s = _session(tmp_path)
    assert s.types() == ["PERSON"]
    values = dict(s.values_for("PERSON"))      # {valeur: occurrences}
    assert values == {"Claire Martin": 2, "Paul Durand": 1}


def test_count_retained_all_by_default(tmp_path):
    s = _session(tmp_path)
    assert s.count_retained("PERSON") == 3     # 2 + 1 occurrences


def test_disable_type(tmp_path):
    s = _session(tmp_path)
    s.set_type_enabled("PERSON", False)
    assert s.count_retained("PERSON") == 0


def test_disable_single_value(tmp_path):
    s = _session(tmp_path)
    s.set_value_enabled("PERSON", "Claire Martin", False)
    assert s.count_retained("PERSON") == 1      # seul "Paul Durand" reste


def test_exclude_column(tmp_path):
    s = _session(tmp_path)
    s.set_column_enabled(0, False)
    assert s.count_retained("PERSON") == 0


def test_exclude_single_cell(tmp_path):
    s = _session(tmp_path)
    s.set_cell_excluded(1, 0, True)             # 1re occurrence de Claire Martin
    assert s.count_retained("PERSON") == 2


def test_unconfirmed_for_cell(tmp_path):
    from anonymator.model import Entity
    src = tmp_path / "f.csv"
    src.write_bytes("Nom;IBAN\nx;FR00\n".encode("cp1252"))
    doc = csv_io.read_csv(src)
    ref = Referential.load_default()
    bad = Entity("IBAN", "FR00", 0, 4, "deterministic", 1.0, confirmed=False)
    s = FileReviewSession(doc, {(1, 1): [bad]}, ref, {1})
    # décochée par défaut → non retenue mais listée comme non confirmée
    assert s.entities_for_cell(1, 1) == []
    assert [e.value for e in s.unconfirmed_for_cell(1, 1)] == ["FR00"]
    # cochée → passe en retenue, sort des non confirmées
    s.set_value_enabled("IBAN", "FR00", True)
    assert s.unconfirmed_for_cell(1, 1) == []
    assert len(s.entities_for_cell(1, 1)) == 1
    # colonne exclue → plus rien à signaler
    s.set_value_enabled("IBAN", "FR00", False)
    s.set_column_enabled(1, False)
    assert s.unconfirmed_for_cell(1, 1) == []


def test_masked_document_and_report(tmp_path):
    s = _session(tmp_path)
    s.set_value_enabled("PERSON", "Paul Durand", False)
    md = s.masked_document()
    assert md.rows[1][0] == "[PERSONNE]"         # Claire Martin masquée
    assert md.rows[3][0] == "Paul Durand"        # décochée → en clair
    rows = s.report().to_rows()
    assert {r["original"] for r in rows} == {"Claire Martin"}
    # le document original n'est pas muté
    assert s.doc.rows[1][0] == "Claire Martin"
