from dataclasses import dataclass
from anonymator.referential import Referential
from anonymator.ner import FakeNer
from anonymator.files.ooxml import scan
from anonymator.files.ooxml.text_unit import TextUnit


@dataclass
class FakeRun:
    text: str


def _ref():
    return Referential.load_default()


def _unit(location, *texts):
    return TextUnit([FakeRun(t) for t in texts], location)


def test_scan_units_detects_per_unit():
    units = [_unit("Corps", "Bonjour Claire Martin"),
             _unit("Corps", "Rien ici")]
    ner = FakeNer({"Claire Martin": "PERSON"})
    scanned = scan.scan_units(units, ner, _ref())
    assert 0 in scanned and 1 not in scanned
    assert scanned[0][0].value == "Claire Martin"


def test_apply_units_masks_and_reports():
    units = [_unit("Tableau L1C1", "Client Claire Martin")]
    ner = FakeNer({"Claire Martin": "PERSON"})
    ref = _ref()
    scanned = scan.scan_units(units, ner, ref)
    report = scan.apply_units(units, scan.confirmed_only(scanned), ref)
    assert units[0].text() == "Client [PERSONNE]"
    rows = report.to_rows()
    assert rows[0]["original"] == "Claire Martin"
    assert rows[0]["locations"] == "Tableau L1C1"


def test_confirmed_only_drops_unconfirmed_and_empties():
    from anonymator.model import Entity
    scanned = {
        0: [Entity("PERSON", "X", 0, 1, "ner", 1.0, confirmed=True)],
        1: [Entity("IBAN", "Y", 0, 1, "deterministic", 1.0, confirmed=False)],
    }
    kept = scan.confirmed_only(scanned)
    assert 0 in kept and 1 not in kept
