from anonymator.model import Entity
from anonymator.core.review_session_base import ReviewSessionBase
from anonymator.referential import Referential


class _Session(ReviewSessionBase):
    """Sous-classe minimale : les entités sont rangées sous des clés entières."""

    def __init__(self, groups, ref):
        super().__init__(ref)
        self._groups = groups
        self._index(groups.values())

    def _keys(self):
        return self._groups.keys()

    def _retained(self, key):
        return self._kept(self._groups.get(key, []))


def _ent(etype, value, confirmed=True):
    return Entity(etype, value, 0, len(value), "deterministic", 1.0, confirmed)


def _session(**kwargs):
    return _Session(kwargs.pop("groups"), Referential.load_default())


def test_counts_distinct_values_and_occurrences():
    s = _session(groups={0: [_ent("PERSON", "Claire Martin")],
                         1: [_ent("PERSON", "Claire Martin")],
                         2: [_ent("PERSON", "Paul Durand")]})
    assert s.types() == ["PERSON"]
    assert dict(s.values_for("PERSON")) == {"Claire Martin": 2, "Paul Durand": 1}
    assert s.total_occurrences() == 3
    assert s.count_retained("PERSON") == 3


def test_unconfirmed_value_is_opt_in():
    s = _session(groups={0: [_ent("IBAN", "FR00", confirmed=False)]})
    assert s.is_value_enabled("IBAN", "FR00") is False
    assert s.is_value_confirmed("IBAN", "FR00") is False
    assert s.count_retained("IBAN") == 0
    assert [e.value for e in s._pending(s._groups[0])] == ["FR00"]


def test_reindex_keeps_user_choices_and_drops_vanished_types():
    """Réindexer est l'opération de base d'un forçage de colonne : elle doit
    recalculer les comptes sans effacer ce que l'utilisateur a décoché."""
    s = _session(groups={0: [_ent("PERSON", "Claire Martin")],
                         1: [_ent("ORG", "Bureau Sablons")]})
    s.set_value_enabled("PERSON", "Claire Martin", False)
    s.set_type_enabled("ORG", False)
    s._groups = {0: [_ent("PERSON", "Claire Martin")],
                 1: [_ent("PERSON", "Paul Durand")]}
    s._index(s._groups.values())
    assert s.types() == ["PERSON"]                      # ORG a disparu
    assert s.is_value_enabled("PERSON", "Claire Martin") is False   # choix gardé
    assert s.is_value_enabled("PERSON", "Paul Durand") is True
    assert dict(s.values_for("PERSON")) == {"Claire Martin": 1, "Paul Durand": 1}


def test_counts_retained_returns_every_type_in_one_pass():
    s = _session(groups={0: [_ent("PERSON", "Claire Martin")],
                         1: [_ent("ORG", "Bureau Sablons")]})
    assert s.counts_retained() == {"PERSON": 1, "ORG": 1}
    s.set_type_enabled("ORG", False)
    assert s.counts_retained() == {"PERSON": 1}
