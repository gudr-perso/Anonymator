"""Un second « Anonymiser & enregistrer » doit rendre le même fichier.

Les sessions classeur et document tiennent un objet ouvert et le masquent en
place. Sans remise à zéro, le second passage réappliquait les offsets d'origine
sur un texte déjà masqué : « [PERSONNE] » devenait « [PERSONNE]NNE] », sans
aucun signe. Le cas se produit dès que l'utilisateur enregistre, décoche une
valeur, et enregistre de nouveau.
"""
import zipfile

import openpyxl

from anonymator.core.ooxml_review_session import OoxmlReviewSession
from anonymator.core.xlsx_review_session import XlsxReviewSession
from anonymator.files import xlsx_io
from anonymator.files.ooxml import scan
from anonymator.files.ooxml.text_unit import TextUnit
from anonymator.ner import NullNer
from anonymator.referential import Referential


class _Run:
    """Run minimal : un objet exposant un `.text` mutable."""
    def __init__(self, text=""):
        self.text = text


def _ooxml_session(text):
    ref = Referential.load_default()
    units = [TextUnit([_Run(text)], "Corps")]
    scanned = scan.scan_units(units, NullNer(), ref)
    session = OoxmlReviewSession(units, scanned, ref,
                                 save_fn=lambda out: None,
                                 post_fn=lambda out, rep: None)
    return session, units


def test_ooxml_second_save_is_identical(tmp_path):
    session, units = _ooxml_session("Contact: jean@ex.com et paul@ex.com")
    session.apply_and_save(tmp_path / "a.docx")
    first = units[0].text()
    session.apply_and_save(tmp_path / "b.docx")
    assert units[0].text() == first == "Contact: [EMAIL] et [EMAIL]"


def test_ooxml_second_save_honours_a_new_choice(tmp_path):
    session, units = _ooxml_session("Contact: jean@ex.com et paul@ex.com")
    session.apply_and_save(tmp_path / "a.docx")
    session.set_value_enabled("EMAIL", "paul@ex.com", False)
    session.apply_and_save(tmp_path / "b.docx")
    assert units[0].text() == "Contact: [EMAIL] et paul@ex.com"


def _workbook(path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["contact_nom", "note"])
    ws.append(["Dupont", "libre"])
    ws.append(["Martin", "libre"])
    wb.properties.creator = "Jean Dupont"
    wb.properties.title = "Paie 2026"
    wb.save(path)
    return path


def _xlsx_session(tmp_path):
    ref = Referential.load_default()
    result = xlsx_io.scan_workbook(_workbook(tmp_path / "b.xlsx"), NullNer(), ref)
    return XlsxReviewSession(result, ref), result


def test_xlsx_second_save_is_identical(tmp_path):
    session, result = _xlsx_session(tmp_path)
    session.apply_and_save(tmp_path / "a.xlsx")
    first = [c.value for c in result.workbook["Sheet"]["A"]]
    session.apply_and_save(tmp_path / "b.xlsx")
    assert [c.value for c in result.workbook["Sheet"]["A"]] == first
    assert first[1:] == ["[PERSONNE]", "[PERSONNE]"]


def test_xlsx_second_save_honours_a_new_choice(tmp_path):
    session, result = _xlsx_session(tmp_path)
    session.apply_and_save(tmp_path / "a.xlsx")
    session.set_value_enabled("PERSON", "Martin", False)
    session.apply_and_save(tmp_path / "b.xlsx")
    assert [c.value for c in result.workbook["Sheet"]["A"]][1:] == ["[PERSONNE]",
                                                                   "Martin"]


def test_xlsx_review_purges_document_properties(tmp_path):
    # Lecture du XML livré, pas de l'objet openpyxl : à la relecture, une
    # propriété absente reprend la valeur par défaut « openpyxl ».
    session, _result = _xlsx_session(tmp_path)
    out = tmp_path / "a.xlsx"
    report = session.apply_and_save(out)
    with zipfile.ZipFile(out) as z:
        core = z.read("docProps/core.xml").decode("utf-8")
    assert "Jean Dupont" not in core and "Paie 2026" not in core
    assert {r["original"] for r in report.to_rows() if r["type"] == "META"} == {
        "Jean Dupont", "Paie 2026"}


def test_xlsx_second_save_does_not_re_report_metadata(tmp_path):
    session, _result = _xlsx_session(tmp_path)
    session.apply_and_save(tmp_path / "a.xlsx")
    report = session.apply_and_save(tmp_path / "b.xlsx")
    assert [r for r in report.to_rows() if r["type"] == "META"] == []
