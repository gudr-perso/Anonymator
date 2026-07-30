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


def test_mask_submenu_offers_inactive_types_and_neutral(qtbot, tmp_path):
    """Un forçage étant une décision explicite, « tout anonymiser » propose
    aussi les types inactifs (POSTAL_CODE) et une entrée neutre [MASQUÉ] pour
    les colonnes sans type — sinon on ne peut masquer ni le code postal ni la
    catégorie."""
    s = _reviewed(qtbot, tmp_path)
    _menu, actions = s._build_column_menu(2)
    types = {etype for (_mode, etype) in actions.values() if etype}
    assert "PERSON" in types            # actif
    assert "POSTAL_CODE" in types       # inactif, désormais forçable
    assert "MASK" in types              # masquage neutre


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


def test_forcing_an_inactive_type_actually_masks(qtbot, tmp_path):
    """Bout en bout : forcer « code postal » (POSTAL_CODE inactif) écrit [CP]
    dans le fichier — le forçage passe outre l'état du référentiel."""
    src = tmp_path / "cp.csv"
    src.write_bytes("code_postal;note\n37000;RAS\n44000;RAS\n".encode("cp1252"))
    s = _screen(tmp_path); qtbot.addWidget(s)
    s.load_path(str(src)); s.header_switch.setChecked(True)
    s.analyze()
    qtbot.waitUntil(lambda: s.session is not None, timeout=5000)
    s.apply_column_override(0, MASK, "POSTAL_CODE")
    res = s.run(when=datetime(2026, 1, 2, 3, 4, 5))
    out = res.output_path.read_bytes().decode("cp1252")
    assert out == "code_postal;note\n[CP];RAS\n[CP];RAS\n"


def test_neutral_mask_hides_a_nomenclature_column(qtbot, tmp_path):
    """Forcer « secteur » en masquage neutre le vide en [MASQUÉ] sans
    l'étiqueter d'un type sémantique."""
    s = _reviewed(qtbot, tmp_path)
    s.apply_column_override(1, MASK, "MASK")
    res = s.run(when=datetime(2026, 1, 2, 3, 4, 5))
    # ce CSV ASCII est détecté UTF-8 : le tag neutre accentué est écrit en
    # UTF-8, on le relit donc en UTF-8 (et non cp1252 comme les tags ASCII)
    out = res.output_path.read_bytes().decode("utf-8")
    lines = out.splitlines()
    # tag neutre lu du référentiel : évite un littéral accentué dans la source
    neutral = Referential.load_default().tag_for("MASK")
    assert lines[0] == "contact_nom;secteur;note"          # titres intacts
    # col0 auto-masquée en [PERSONNE], col1 forcée en neutre, col2 libre
    assert lines[1] == f"[PERSONNE];{neutral};RAS"
    assert lines[2] == f"[PERSONNE];{neutral};a rappeler"


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


def test_column_override_survives_a_header_change(qtbot, tmp_path):
    """Basculer « première ligne = en-têtes » déplace des lignes, jamais des
    colonnes : l'arbitrage positionnel garde son sens et doit être reporté."""
    from unittest.mock import patch
    from PySide6.QtWidgets import QMessageBox
    s = _reviewed(qtbot, tmp_path)
    s.apply_column_override(2, MASK, "ORG")
    with patch("anonymator.ui.file_screen.QMessageBox.question",
               return_value=QMessageBox.Yes):
        s.header_switch.setChecked(False)
    s.analyze()
    qtbot.waitUntil(lambda: s.session is not None, timeout=5000)
    assert s.session.column_override(2) == (MASK, "ORG")
    assert s.session.count_retained("ORG") == 3     # la ligne 1 est devenue donnée


def test_override_of_a_vanished_column_is_dropped(qtbot, tmp_path):
    """Reporter un arbitrage sur un fichier plus étroit ne doit pas lever."""
    from unittest.mock import patch
    from PySide6.QtWidgets import QMessageBox
    s = _reviewed(qtbot, tmp_path)
    s.apply_column_override(2, MASK, "ORG")
    with patch("anonymator.ui.file_screen.QMessageBox.question",
               return_value=QMessageBox.Yes):
        s.header_switch.setChecked(False)
    other = tmp_path / "etroit.csv"
    other.write_bytes("Nom;Ville\nLeclerc;Tours\n".encode("cp1252"))
    s.load_path(str(other))
    s.analyze()
    qtbot.waitUntil(lambda: s.session is not None, timeout=5000)
    assert s.session.column_overrides() == {}       # arbitrage d'un autre fichier
