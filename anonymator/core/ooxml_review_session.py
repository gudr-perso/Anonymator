from anonymator.model import Entity
from anonymator.files.ooxml import scan


class OoxmlReviewSession:
    """État de revue d'un document docx/pptx (non-Qt). Contrôle à deux
    niveaux combinés en ET : type activé, valeur distincte activée. Miroir de
    FileReviewSession sans la dimension colonnes/cellules (clé = index d'unité).

    En mode revue, l'arbre couvre les entités des parties principales ;
    commentaires/notes docx et métadonnées sont traités par `post_fn`
    (entités confirmées) au moment de l'application."""

    def __init__(self, units, scanned: dict[int, list[Entity]], ref,
                 save_fn, post_fn):
        self._units = units
        self._scanned = scanned
        self._ref = ref
        self._save_fn = save_fn
        self._post_fn = post_fn
        self._types_enabled: dict[str, bool] = {}
        self._values_enabled: dict[tuple[str, str], bool] = {}
        self._values_count: dict[tuple[str, str], int] = {}
        self._values_confirmed: dict[tuple[str, str], bool] = {}
        for ents in scanned.values():
            for e in ents:
                self._types_enabled.setdefault(e.type, True)
                key = (e.type, e.value)
                self._values_count[key] = self._values_count.get(key, 0) + 1
                self._values_enabled.setdefault(key, e.confirmed)
                # non confirmé si une occurrence échoue au contrôle de la clé
                self._values_confirmed[key] = (
                    self._values_confirmed.get(key, True) and e.confirmed)

    # --- lecture ---
    def types(self) -> list[str]:
        return sorted(self._types_enabled)

    def total_occurrences(self) -> int:
        return sum(self._values_count.values())

    def values_for(self, etype: str) -> list[tuple[str, int]]:
        items = [(v, n) for (t, v), n in self._values_count.items() if t == etype]
        return sorted(items)

    def _unit_retained(self, i: int) -> list[Entity]:
        out = []
        for e in self._scanned.get(i, []):
            if not self._types_enabled.get(e.type, True):
                continue
            if not self._values_enabled.get((e.type, e.value), True):
                continue
            out.append(e)
        return out

    def count_retained(self, etype: str) -> int:
        return sum(1 for i in self._scanned
                   for e in self._unit_retained(i) if e.type == etype)

    def entities_for_unit(self, i: int) -> list[Entity]:
        return self._unit_retained(i)

    def unconfirmed_for_unit(self, i: int) -> list[Entity]:
        """Entités de l'unité au format valide mais clé invalide, décochées par
        défaut : à surligner distinctement (non masquées, opt-in)."""
        out = []
        for e in self._scanned.get(i, []):
            if not self._types_enabled.get(e.type, True):
                continue
            if e.confirmed or self._values_enabled.get((e.type, e.value), True):
                continue
            out.append(e)
        return out

    def is_type_enabled(self, etype: str) -> bool:
        return self._types_enabled.get(etype, True)

    def is_value_enabled(self, etype: str, value: str) -> bool:
        return self._values_enabled.get((etype, value), True)

    def is_value_confirmed(self, etype: str, value: str) -> bool:
        """Faux = format reconnu mais contrôle de la clé (checksum) échoué."""
        return self._values_confirmed.get((etype, value), True)

    # --- écriture ---
    def set_type_enabled(self, etype: str, enabled: bool) -> None:
        self._types_enabled[etype] = enabled

    def set_value_enabled(self, etype: str, value: str, enabled: bool) -> None:
        self._values_enabled[(etype, value)] = enabled

    # --- production ---
    def apply_and_save(self, out_path):
        retained = {i: self._unit_retained(i) for i in self._scanned}
        retained = {i: v for i, v in retained.items() if v}
        report = scan.apply_units(self._units, retained, self._ref)
        self._save_fn(out_path)
        self._post_fn(out_path, report)
        return report
