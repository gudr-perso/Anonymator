from datetime import datetime
from pathlib import Path
from anonymator.referential import Referential
from anonymator.ner import FakeNer
from anonymator.files import csv_io
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

def test_numeric_phone_column_is_masked(tmp_path):
    """Régression : une colonne sans lettre n'était jamais analysée, donc une
    colonne de téléphones sortait en clair."""
    src = tmp_path / "t.csv"
    src.write_bytes(
        ("reference;telephone\n"
         "X1;03 73 41 92 92\n"
         "X2;05 32 14 00 01\n").encode("cp1252"))
    ref = Referential.load_default()
    result = anonymize_csv(src, FakeNer({}), ref, tmp_path,
                           when=datetime(2026, 1, 1, 0, 0, 0))
    out = result.output_path.read_bytes().decode("cp1252")
    assert out == "reference;telephone\nX1;[TEL]\nX2;[TEL]\n"


def test_typed_column_masks_rows_the_model_missed(tmp_path):
    """Le NER ne reconnaît qu'un nom sur deux ; l'en-tête tranche pour toute
    la colonne."""
    src = tmp_path / "c.csv"
    src.write_bytes(
        ("contact_nom;ca\n"
         "Leclerc;100\n"
         "Berger;200\n").encode("cp1252"))
    ref = Referential.load_default()
    result = anonymize_csv(src, FakeNer({"Leclerc": "PERSON"}), ref, tmp_path,
                           when=datetime(2026, 1, 1, 0, 0, 0))
    out = result.output_path.read_bytes().decode("cp1252")
    assert out == "contact_nom;ca\n[PERSONNE];100\n[PERSONNE];200\n"


def test_nomenclature_column_is_left_intact(tmp_path):
    """Un axe d'analyse (secteur) ne doit pas être masqué, même si le modèle
    y voit des organisations."""
    secteurs = ["Industrie", "BTP", "Textile"]
    lignes = ["reference;secteur;ca"]
    for i in range(24):
        lignes.append("X%d;%s;%d" % (i, secteurs[i % 3], 1000 + i))
    src = tmp_path / "n.csv"
    src.write_bytes(("\n".join(lignes) + "\n").encode("cp1252"))
    ref = Referential.load_default()
    result = anonymize_csv(src, FakeNer({"Industrie": "ORG", "BTP": "ORG"}),
                           ref, tmp_path, when=datetime(2026, 1, 1, 0, 0, 0))
    out = result.output_path.read_bytes().decode("cp1252")
    assert "[ORG]" not in out
    assert out.count("Industrie") == 8


def test_explicit_include_overrides_skipped_column(tmp_path):
    """Une colonne exclue par défaut reste analysable sur demande."""
    lignes = (["reference;secteur;ca"]
              + ["X%d;Industrie;%d" % (i, 1000 + i) for i in range(24)])
    src = tmp_path / "i.csv"
    src.write_bytes(("\n".join(lignes) + "\n").encode("cp1252"))
    ref = Referential.load_default()
    result = anonymize_csv(src, FakeNer({"Industrie": "ORG"}), ref, tmp_path,
                           when=datetime(2026, 1, 1, 0, 0, 0), include={1})
    out = result.output_path.read_bytes().decode("cp1252")
    assert "Industrie" not in out and out.count("[ORG]") == 24


def test_column_overrides_exclude(tmp_path):
    src = tmp_path / "x.csv"
    src.write_bytes("Nom;Note\nClaire Martin;RAS Claire Martin\n".encode("cp1252"))
    ref = Referential.load_default()
    ner = FakeNer({"Claire Martin": "PERSON"})
    result = anonymize_csv(src, ner, ref, tmp_path,
                           when=datetime(2026, 1, 1, 0, 0, 0), exclude={1})
    out = result.output_path.read_bytes().decode("cp1252")
    assert out == "Nom;Note\n[PERSONNE];RAS Claire Martin\n"


def _no_sniff_header(tmp_path):
    """Fichier 100 % texte : csv.Sniffer n'y voit pas d'en-tête."""
    src = tmp_path / "h.csv"
    src.write_bytes(("contact_nom;secteur\n"
                     "Leclerc;Industrie\n"
                     "Berger;BTP\n").encode("cp1252"))
    return src


def test_has_header_override_enables_column_typing(tmp_path):
    src = _no_sniff_header(tmp_path)
    ref = Referential.load_default()
    assert csv_io.read_csv(src).has_header is False      # prérequis du test
    result = anonymize_csv(src, FakeNer({}), ref, tmp_path,
                           when=datetime(2026, 1, 1, 0, 0, 0), has_header=True)
    out = result.output_path.read_bytes().decode("cp1252")
    assert out == ("contact_nom;secteur\n"
                   "[PERSONNE];Industrie\n"
                   "[PERSONNE];BTP\n")


def test_has_header_override_can_force_first_row_as_data(tmp_path):
    src = tmp_path / "d.csv"
    src.write_bytes(("Claire Martin;100\n"
                     "Hugo Dupont;200\n").encode("cp1252"))
    ref = Referential.load_default()
    ner = FakeNer({"Claire Martin": "PERSON", "Hugo Dupont": "PERSON"})
    result = anonymize_csv(src, ner, ref, tmp_path,
                           when=datetime(2026, 1, 1, 0, 0, 0), has_header=False)
    out = result.output_path.read_bytes().decode("cp1252")
    assert out == "[PERSONNE];100\n[PERSONNE];200\n"
