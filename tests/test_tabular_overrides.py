import pytest

from anonymator.model import Entity
from anonymator.referential import Referential
from anonymator.files.columns import ColumnPlan, SKIP, TEXT, TYPED
from anonymator.core.tabular_review_session import (
    AUTO, CLEAR, MASK, TabularReviewSession)


class _Grid(TabularReviewSession):
    """Tableau minimal en mémoire : clé de cellule (ligne, colonne)."""

    def __init__(self, rows, scanned, ref, maskable, plans):
        self.rows = rows
        super().__init__(scanned, ref, maskable, plans)

    def column_of(self, cell_key):
        return cell_key[1]

    def has_column(self, col_key):
        return 0 <= col_key < max((len(r) for r in self.rows), default=0)

    def column_values(self, col_key):
        return {(r, col_key): row[col_key]
                for r, row in enumerate(self.rows) if col_key < len(row)}


def _ent(etype, value):
    return Entity(etype, value, 0, len(value), "ner", 1.0)


def _grid():
    rows = [["Claire Martin", "Industrie", "note libre"],
            ["Paul Durand", "BTP", "autre note"],
            ["", "Textile", "troisieme"]]
    plans = {0: ColumnPlan(TYPED, "PERSON", "en-tête « nom »"),
             1: ColumnPlan(SKIP, reason="nomenclature (peu de valeurs distinctes)"),
             2: ColumnPlan(TEXT, reason="texte libre")}
    scanned = {(0, 0): [_ent("PERSON", "Claire Martin")],
               (1, 0): [_ent("PERSON", "Paul Durand")]}
    return _Grid(rows, scanned, Referential.load_default(), {0, 2}, plans)


def test_default_state_is_auto():
    g = _grid()
    assert g.column_override(0) == (AUTO, None)
    assert g.count_retained("PERSON") == 2


def test_column_reason_is_exposed():
    g = _grid()
    assert g.column_reason(1) == "nomenclature (peu de valeurs distinctes)"


def test_clear_takes_a_column_out_of_scope():
    g = _grid()
    g.set_column_override(0, CLEAR)
    assert g.column_override(0) == (CLEAR, None)
    assert g.count_retained("PERSON") == 0
    assert g.retained_by_cell() == {}


def test_mask_covers_every_non_empty_cell_even_undetected():
    """L'état « tout anonymiser » n'existe sur aucun chemin de détection : il
    fabrique une entité couvrant la cellule, comme la politique TYPED."""
    g = _grid()
    g.set_column_override(2, MASK, "ORG")
    kept = g.retained_by_cell()
    assert [kept[(r, 2)][0].value for r in (0, 1, 2)] == [
        "note libre", "autre note", "troisieme"]
    assert g.count_retained("ORG") == 3
    assert dict(g.values_for("ORG")) == {
        "note libre": 1, "autre note": 1, "troisieme": 1}


def test_mask_skips_empty_cells():
    g = _grid()
    g.set_column_override(0, MASK, "PERSON")
    assert (2, 0) not in g.retained_by_cell()      # cellule vide
    assert g.count_retained("PERSON") == 2


def test_mask_on_a_skipped_column_works():
    """Une colonne écartée par le plan (nomenclature) reste forçable : c'est
    tout l'intérêt de l'override."""
    g = _grid()
    g.set_column_override(1, MASK, "ORG")
    assert g.count_retained("ORG") == 3


def test_auto_restores_the_computed_plan():
    g = _grid()
    g.set_column_override(0, MASK, "ORG")
    g.set_column_override(0, AUTO)
    assert g.column_override(0) == (AUTO, None)
    assert g.count_retained("PERSON") == 2
    assert g.count_retained("ORG") == 0


def test_forced_values_stay_decheckable():
    g = _grid()
    g.set_column_override(2, MASK, "ORG")
    g.set_value_enabled("ORG", "autre note", False)
    assert g.count_retained("ORG") == 2


def test_user_choices_survive_a_later_override():
    g = _grid()
    g.set_value_enabled("PERSON", "Paul Durand", False)
    g.set_column_override(2, MASK, "ORG")          # déclenche un réindexage
    assert g.is_value_enabled("PERSON", "Paul Durand") is False
    assert g.count_retained("PERSON") == 1


def test_mask_requires_a_type():
    g = _grid()
    with pytest.raises(ValueError):
        g.set_column_override(2, MASK)


def test_inactive_deduced_type_is_still_proposed():
    """POSTAL_CODE est inactif, mais un forçage manuel passe outre le garde
    is_active (cf. detect_column force=True) : on le propose donc quand même,
    déduit du plan, pour le pré-cocher dans « tout anonymiser »."""
    rows = [["37000"], ["44000"]]
    plans = {0: ColumnPlan(TYPED, "POSTAL_CODE", "en-tête « code postal »")}
    g = _Grid(rows, {}, Referential.load_default(), {0}, plans)
    assert g.default_type_for(0) == "POSTAL_CODE"


def test_deduced_type_reflects_the_plan():
    g = _grid()
    assert g.default_type_for(0) == "PERSON"
    assert g.default_type_for(2) is None            # colonne de texte libre


def test_mask_forces_an_inactive_type():
    """Forcer « code postal » (POSTAL_CODE inactif) masque bel et bien la
    colonne : la décision de l'utilisateur prime sur l'état du référentiel."""
    rows = [["37000"], ["44000"], [""]]
    plans = {0: ColumnPlan(TYPED, "POSTAL_CODE", "en-tête « code postal »")}
    g = _Grid(rows, {}, Referential.load_default(), set(), plans)
    g.set_column_override(0, MASK, "POSTAL_CODE")
    assert g.count_retained("POSTAL_CODE") == 2     # la cellule vide est ignorée
    assert set(g.retained_by_cell()) == {(0, 0), (1, 0)}


def test_neutral_mask_hides_a_typeless_column():
    """Une nomenclature (« catégorie ») n'a aucun type d'entité : le masquage
    neutre [MASQUÉ] la vide sans la mal-étiqueter, même hors périmètre auto."""
    g = _grid()                                     # colonne 1 = nomenclature SKIP
    assert g.column_override(1) == (AUTO, None)
    assert g.count_retained("MASK") == 0
    g.set_column_override(1, MASK, "MASK")
    assert g.count_retained("MASK") == 3            # Industrie / BTP / Textile
    assert g.column_override(1) == (MASK, "MASK")


def test_overrides_are_exportable_and_replayable():
    g = _grid()
    g.set_column_override(2, MASK, "ORG")
    g.set_column_override(1, CLEAR)
    assert g.column_overrides() == {2: (MASK, "ORG"), 1: (CLEAR, None)}
    fresh = _grid()
    for key, (mode, etype) in g.column_overrides().items():
        fresh.set_column_override(key, mode, etype)
    assert fresh.count_retained("ORG") == 3
