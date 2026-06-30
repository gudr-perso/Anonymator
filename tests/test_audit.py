import json
from pathlib import Path
from anonymator.report.audit import AuditReport


def test_report_tracks_confirmed_flag():
    rep = AuditReport()
    rep.add("IBAN", "FR00 0000", "[IBAN]", "texte", confirmed=False)
    row = rep.to_rows()[0]
    assert row["confirme"] == "non"


def test_report_confirmed_defaults_yes():
    rep = AuditReport()
    rep.add("PERSON", "Claire", "[PERSONNE]", "texte")
    assert rep.to_rows()[0]["confirme"] == "oui"


def test_aggregates_by_type_and_value():
    rep = AuditReport()
    rep.add("PERSON", "Claire Martin", "[PERSONNE]", "CompAuxLib L2")
    rep.add("PERSON", "Claire Martin", "[PERSONNE]", "CompAuxLib L9")
    rep.add("EMAIL", "c@x.fr", "[EMAIL]", "EcritureLib L2")
    rows = rep.to_rows()
    person = next(r for r in rows if r["original"] == "Claire Martin")
    assert person["type"] == "PERSON"
    assert person["tag"] == "[PERSONNE]"
    assert person["occurrences"] == 2
    assert person["locations"] == "CompAuxLib L2; CompAuxLib L9"


def test_export_json_and_csv(tmp_path):
    rep = AuditReport()
    rep.add("EMAIL", "c@x.fr", "[EMAIL]", "texte")
    j = tmp_path / "r.json"
    rep.export_json(j)
    data = json.loads(j.read_text(encoding="utf-8"))
    assert data[0]["original"] == "c@x.fr"
    c = tmp_path / "r.csv"
    rep.export_csv(c)
    content = c.read_text(encoding="utf-8")
    assert "type" in content and "c@x.fr" in content
