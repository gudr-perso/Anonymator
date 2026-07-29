"""Socle commun aux revues (CSV, classeur, docx/pptx).

La comptabilité type/valeur est la même partout : c'est elle qui alimente
l'arbre « Entités détectées » et ses cases à cocher. Ce qui change d'un format
à l'autre, c'est la clé sous laquelle les entités sont rangées — cellule pour
un tableau, index d'unité pour un document — et c'est tout ce qu'une
sous-classe a à fournir."""

from anonymator.model import Entity


class ReviewSessionBase:
    def __init__(self, ref):
        self.ref = ref
        self._types_enabled: dict[str, bool] = {}
        self._values_enabled: dict[tuple[str, str], bool] = {}
        self._values_count: dict[tuple[str, str], int] = {}
        self._values_confirmed: dict[tuple[str, str], bool] = {}

    def _index(self, groups) -> None:
        """(Re)construit la comptabilité à partir de groupes d'entités.

        Rejouable : les arbitrages déjà pris par l'utilisateur sont conservés,
        tout le reste est recalculé. C'est ce qui permet à un forçage de
        colonne d'ajouter ou de retirer des entités sans tenir de comptes
        différentiels — un compte différentiel finit toujours par dériver."""
        prev_types, prev_values = self._types_enabled, self._values_enabled
        self._types_enabled = {}
        self._values_enabled = {}
        self._values_count = {}
        self._values_confirmed = {}
        for ents in groups:
            for e in ents:
                self._types_enabled.setdefault(e.type, prev_types.get(e.type, True))
                key = (e.type, e.value)
                self._values_count[key] = self._values_count.get(key, 0) + 1
                # défaut : confirmé → activé ; non confirmé → désactivé (opt-in)
                self._values_enabled.setdefault(
                    key, prev_values.get(key, e.confirmed))
                # non confirmé si une occurrence échoue au contrôle de la clé
                self._values_confirmed[key] = (
                    self._values_confirmed.get(key, True) and e.confirmed)

    # --- lecture ---
    def types(self) -> list[str]:
        return sorted(self._types_enabled)

    def total_occurrences(self) -> int:
        """Nombre total d'occurrences détectées (toutes valeurs, tous types)."""
        return sum(self._values_count.values())

    def values_for(self, etype: str) -> list[tuple[str, int]]:
        items = [(v, n) for (t, v), n in self._values_count.items() if t == etype]
        return sorted(items)

    def is_type_enabled(self, etype: str) -> bool:
        return self._types_enabled.get(etype, True)

    def is_value_enabled(self, etype: str, value: str) -> bool:
        """État de la case d'une valeur distincte (pour cocher l'UI)."""
        return self._values_enabled.get((etype, value), True)

    def is_value_confirmed(self, etype: str, value: str) -> bool:
        """Faux = format reconnu mais contrôle de la clé (checksum) échoué."""
        return self._values_confirmed.get((etype, value), True)

    # --- écriture ---
    def set_type_enabled(self, etype: str, enabled: bool) -> None:
        self._types_enabled[etype] = enabled

    def set_value_enabled(self, etype: str, value: str, enabled: bool) -> None:
        self._values_enabled[(etype, value)] = enabled

    # --- filtres partagés ---
    def _kept(self, ents: list[Entity]) -> list[Entity]:
        return [e for e in ents
                if self._types_enabled.get(e.type, True)
                and self._values_enabled.get((e.type, e.value), True)]

    def _pending(self, ents: list[Entity]) -> list[Entity]:
        """Entités au format valide mais clé invalide, décochées par défaut :
        à surligner distinctement (non masquées, opt-in)."""
        return [e for e in ents
                if self._types_enabled.get(e.type, True)
                and not e.confirmed
                and not self._values_enabled.get((e.type, e.value), True)]

    # --- à fournir par les sous-classes ---
    def _keys(self):
        raise NotImplementedError

    def _retained(self, key) -> list[Entity]:
        raise NotImplementedError

    # --- comptes ---
    def counts_retained(self) -> dict[str, int]:
        """Occurrences retenues par type, en une seule passe.

        L'arbre en redemande un par type à chaque clic : les compter séparément
        relit tout le fichier une fois par type, ce qui se voit sur une colonne
        forcée de 100 000 lignes."""
        out: dict[str, int] = {}
        for key in self._keys():
            for e in self._retained(key):
                out[e.type] = out.get(e.type, 0) + 1
        return out

    def count_retained(self, etype: str) -> int:
        return self.counts_retained().get(etype, 0)
