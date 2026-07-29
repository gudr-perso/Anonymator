from datetime import datetime, date
import openpyxl
from openpyxl.styles import Font
from anonymator.referential import Referential
from anonymator.ner import FakeNer, NullNer
from anonymator.files.anonymize_file import anonymize_xlsx
from anonymator.files.xlsx_io import sheet_has_header


def _anonymize(src, tmp_path, ner):
    return anonymize_xlsx(src, ner, Referential.load_default(), tmp_path,
                          when=datetime(2026, 6, 24, 17, 18, 0))

def _make_book(path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Balance"
    ws["A1"] = "Libellé"; ws["B1"] = "Montant"
    ws["A1"].font = Font(bold=True)
    ws["A2"] = "Claire Martin"; ws["B2"] = 100
    ws["B3"] = "=B2*2"
    ws2 = wb.create_sheet("Tiers")
    ws2["A1"] = "Fournisseur Claire Martin"
    wb.save(path)

def test_masks_string_cells_all_sheets_preserves_formatting(tmp_path):
    src = tmp_path / "bal.xlsx"
    _make_book(src)
    ref = Referential.load_default()
    ner = FakeNer({"Claire Martin": "PERSON"})
    res = anonymize_xlsx(src, ner, ref, tmp_path,
                         when=datetime(2026, 6, 24, 17, 18, 0))
    assert res.output_path.name == "bal_ano_20260624171800.xlsx"
    wb = openpyxl.load_workbook(res.output_path)
    ws = wb["Balance"]
    assert ws["A2"].value == "[PERSONNE]"
    assert ws["B2"].value == 100
    assert ws["B3"].value == "=B2*2"
    assert ws["A1"].font.bold is True
    assert ws["A1"].value == "Libellé"
    assert wb["Tiers"]["A1"].value == "Fournisseur [PERSONNE]"
    assert openpyxl.load_workbook(src)["Balance"]["A2"].value == "Claire Martin"
    assert any(r["original"] == "Claire Martin" for r in res.report.to_rows())


def _clients_book(path, n=24):
    """Feuille type extraction client : en-têtes explicites, colonnes mêlant
    identités, mesures et nomenclature."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Clients"
    for c, h in enumerate(["code_client", "contact_nom", "telephone",
                           "secteur", "ca_2025", "date_entree"], start=1):
        ws.cell(row=1, column=c, value=h)
    secteurs = ["Industrie", "BTP", "Textile"]
    for i in range(n):
        r = i + 2
        ws.cell(row=r, column=1, value="C%07d" % (i + 1))
        ws.cell(row=r, column=2, value=["Leclerc", "Berger", "Poirier"][i % 3])
        ws.cell(row=r, column=3, value="03 73 41 92 %02d" % i)
        ws.cell(row=r, column=4, value=secteurs[i % 3])
        ws.cell(row=r, column=5, value=1000 + i)
        ws.cell(row=r, column=6, value=date(2020, 1, 1 + (i % 28)))
    wb.save(path)


def test_xlsx_typed_column_masks_every_row_without_model(tmp_path):
    """Le typage par en-tête ne dépend pas du NER : sans modèle, la colonne
    de noms et celle de téléphones sont traitées intégralement."""
    src = tmp_path / "clients.xlsx"
    _clients_book(src)
    res = _anonymize(src, tmp_path, NullNer())
    ws = openpyxl.load_workbook(res.output_path)["Clients"]
    assert [ws.cell(row=r, column=2).value for r in (2, 3, 4)] == ["[PERSONNE]"] * 3
    assert [ws.cell(row=r, column=3).value for r in (2, 3, 4)] == ["[TEL]"] * 3


def test_xlsx_direct_path_skips_unconfirmed_like_csv(tmp_path):
    """Chemin direct, sans revue : une entité au format plausible mais dont le
    contrôle de clé échoue (ici un IBAN à checksum invalide) n'est pas masquée,
    exactement comme sur le chemin CSV. Sans revue pour l'opt-in, la prudence
    est de la laisser en clair plutôt que de masquer une fausse détection."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Notes"
    ws["A1"] = "commentaire"
    ws["A2"] = "voir IBAN FR7612345678901234567890123"    # checksum KO
    ws["A3"] = "IBAN FR7630006000011234567890189 conforme"  # checksum OK
    src = tmp_path / "notes.xlsx"
    wb.save(src)
    res = _anonymize(src, tmp_path, NullNer())
    out = openpyxl.load_workbook(res.output_path)["Notes"]
    assert "FR7612345678901234567890123" in out["A2"].value   # non confirmé : intact
    assert "[IBAN]" in out["A3"].value                        # confirmé : masqué


def test_xlsx_keeps_nomenclature_and_measures(tmp_path):
    src = tmp_path / "clients.xlsx"
    _clients_book(src)
    res = _anonymize(src, tmp_path, FakeNer({"Industrie": "ORG", "BTP": "ORG"}))
    ws = openpyxl.load_workbook(res.output_path)["Clients"]
    assert ws.cell(row=2, column=4).value == "Industrie"
    assert ws.cell(row=2, column=5).value == 1000
    assert ws.cell(row=2, column=6).value == datetime(2020, 1, 1)


def test_xlsx_header_row_is_never_masked(tmp_path):
    src = tmp_path / "clients.xlsx"
    _clients_book(src)
    res = _anonymize(src, tmp_path, NullNer())
    ws = openpyxl.load_workbook(res.output_path)["Clients"]
    assert ws.cell(row=1, column=2).value == "contact_nom"
    assert ws.cell(row=1, column=3).value == "telephone"


def test_xlsx_report_locates_masked_cells(tmp_path):
    src = tmp_path / "clients.xlsx"
    _clients_book(src)
    res = _anonymize(src, tmp_path, NullNer())
    rows = res.report.to_rows()
    assert any(r["type"] == "PHONE" for r in rows)
    assert any(r["type"] == "PERSON" for r in rows)


def _all_text_book(path, headers, n=24):
    """Feuille dont aucune colonne n'est typée : le signal des types de
    cellules est aveugle."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Feuille"
    for c, h in enumerate(headers, start=1):
        ws.cell(row=1, column=c, value=h)
    for i in range(n):
        ws.cell(row=i + 2, column=1, value=["Leclerc", "Berger", "Poirier"][i % 3])
        ws.cell(row=i + 2, column=2, value="La Rochelle" if i % 2 else "Nantes")
        ws.cell(row=i + 2, column=3, value=["Industrie", "BTP", "Textile"][i % 3])
    wb.save(path)
    return wb


def test_sheet_has_header_falls_back_on_column_vocabulary(tmp_path):
    """Feuille 100 % textuelle : les types de cellules ne disent rien, mais la
    ligne 1 est faite de noms de colonnes."""
    src = tmp_path / "texte.xlsx"
    _all_text_book(src, ["contact_nom", "ville", "secteur"])
    assert sheet_has_header(openpyxl.load_workbook(src)["Feuille"]) is True


def test_sheet_has_header_stays_false_on_a_data_row(tmp_path):
    src = tmp_path / "sansentete.xlsx"
    _all_text_book(src, ["Claire Martin", "Nantes", "Industrie"])
    assert sheet_has_header(openpyxl.load_workbook(src)["Feuille"]) is False


def test_sheet_has_header_keeps_type_signal_authoritative(tmp_path):
    """Le vocabulaire n'est consulté qu'en dernier recours : une ligne 1 qui
    n'est pas entièrement textuelle reste un refus."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws["A1"] = "contact_nom"; ws["B1"] = 2026        # un nombre en ligne 1
    ws["A2"] = "Leclerc"; ws["B2"] = "Nantes"
    src = tmp_path / "mixte.xlsx"; wb.save(src)
    assert sheet_has_header(openpyxl.load_workbook(src).active) is False


def test_all_text_sheet_is_typed_by_its_headers(tmp_path):
    """Effet visé : le typage par en-tête redevient possible sans modèle."""
    src = tmp_path / "texte.xlsx"
    _all_text_book(src, ["contact_nom", "ville", "secteur"])
    res = _anonymize(src, tmp_path, NullNer())
    ws = openpyxl.load_workbook(res.output_path)["Feuille"]
    assert ws["A1"].value == "contact_nom"          # titres préservés
    assert ws["A2"].value == "[PERSONNE]"
    assert ws["B2"].value == "[ADRESSE]"
    assert ws["C2"].value == "Industrie"            # nomenclature intacte
