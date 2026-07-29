from datetime import datetime

from PySide6.QtCore import Qt

from anonymator.referential import Referential
from anonymator.ner import FakeNer
from anonymator.ui.model_loader import ModelLoader
from anonymator.ui.preferences import Preferences
from anonymator.ui.file_screen import FileScreen
from anonymator.core.tabular_review_session import AUTO, CLEAR, MASK


def _csv(tmp_path):
    src = tmp_path / "clients.csv"
    src.write_bytes(
        ("contact_nom;secteur;note\n"
         "Leclerc;Industrie;RAS\n"
         "Berger;BTP;a rappeler\n").encode("cp1252"))
    return src


def _screen(tmp_path):
    loader = ModelLoader(FakeNer({}))
    return FileScreen(Referential.load_default(), loader,
                      Preferences(output_dir=str(tmp_path)), on_back=lambda: None)


def _reviewed(qtbot, tmp_path):
    s = _screen(tmp_path)
    qtbot.addWidget(s)
    s.load_path(str(_csv(tmp_path)))
    s.header_switch.setChecked(True)
    s.analyze()
    qtbot.waitUntil(lambda: s.session is not None, timeout=5000)
    return s


def test_header_menu_offers_three_states(qtbot, tmp_path):
    s = _reviewed(qtbot, tmp_path)
    menu, actions = s._build_column_menu(2)
    labels = [a.text() for a in menu.actions()]
    assert any(l.startswith("Auto") for l in labels)
    assert "Tout anonymiser" in [a.text() for a in menu.actions() if a.menu()]
    assert "Tout libérer" in labels
    # le sous-menu ne propose que des types actifs
    types = {etype for (_mode, etype) in actions.values() if etype}
    assert "PERSON" in types and "POSTAL_CODE" not in types


def test_header_menu_puts_the_deduced_type_first(qtbot, tmp_path):
    s = _reviewed(qtbot, tmp_path)
    _menu, actions = s._build_column_menu(0)       # colonne « contact_nom »
    masks = [etype for (mode, etype) in actions.values() if mode == MASK]
    assert masks[0] == "PERSON"


def test_forcing_a_column_masks_every_cell(qtbot, tmp_path):
    s = _reviewed(qtbot, tmp_path)
    s.apply_column_override(2, MASK, "ORG")        # colonne « note »
    res = s.run(when=datetime(2026, 1, 2, 3, 4, 5))
    out = res.output_path.read_bytes().decode("cp1252")
    lines = out.splitlines()
    assert lines[0].endswith(";note")              # titres intacts
    assert lines[1].endswith(";[ORG]")
    assert lines[2].endswith(";[ORG]")


def test_freeing_a_column_keeps_it_in_clear(qtbot, tmp_path):
    s = _reviewed(qtbot, tmp_path)
    assert s.session.count_retained("PERSON") > 0
    s.apply_column_override(0, CLEAR)
    res = s.run(when=datetime(2026, 1, 2, 3, 4, 5))
    out = res.output_path.read_bytes().decode("cp1252")
    assert "Leclerc" in out and "[PERSONNE]" not in out


def test_forced_header_is_marked_and_explained(qtbot, tmp_path):
    s = _reviewed(qtbot, tmp_path)
    s.apply_column_override(2, MASK, "ORG")
    item = s.table.horizontalHeaderItem(2)
    assert item.text().endswith("note") and item.text() != "note"   # marqueur
    assert "Organisation" in item.toolTip()


def test_auto_header_tooltip_shows_the_reason(qtbot, tmp_path):
    s = _reviewed(qtbot, tmp_path)
    tip = s.table.horizontalHeaderItem(1).toolTip()   # « secteur » : nomenclature
    assert "nomenclature" in tip or "texte libre" in tip


def test_forced_column_appears_in_the_entity_tree(qtbot, tmp_path):
    s = _reviewed(qtbot, tmp_path)
    s.apply_column_override(2, MASK, "ORG")
    tops = [s.side.topLevelItem(i).data(0, Qt.UserRole)[1]
            for i in range(s.side.topLevelItemCount())]
    assert "ORG" in tops
    assert "occ." in s.occ_badge.text()


def test_returning_to_auto_restores_the_plan(qtbot, tmp_path):
    s = _reviewed(qtbot, tmp_path)
    s.apply_column_override(0, CLEAR)
    assert s.session.count_retained("PERSON") == 0
    s.apply_column_override(0, AUTO)
    assert s.session.count_retained("PERSON") == 2
