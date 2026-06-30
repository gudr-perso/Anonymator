from anonymator.model import Entity


class FileReviewSession:
    """État de revue d'un fichier CSV (non-Qt).

    Quatre niveaux de contrôle combinés en ET : colonne incluse, type activé,
    valeur distincte activée, cellule non exclue individuellement. Une valeur
    démarre activée si ses entités sont `confirmed`, désactivée sinon (opt-in)."""

    def __init__(self, doc, scanned: dict[tuple[int, int], list[Entity]],
                 ref, maskable_cols: set[int]):
        self.doc = doc
        self.ref = ref
        self._cells = scanned
        self._columns_enabled: dict[int, bool] = {c: True for c in maskable_cols}
        self._types_enabled: dict[str, bool] = {}
        self._values_enabled: dict[tuple[str, str], bool] = {}
        self._values_count: dict[tuple[str, str], int] = {}
        self._cells_excluded: set[tuple[int, int]] = set()
        for ents in self._cells.values():
            for e in ents:
                self._types_enabled.setdefault(e.type, True)
                key = (e.type, e.value)
                self._values_count[key] = self._values_count.get(key, 0) + 1
                # défaut : confirmé → activé ; non confirmé → désactivé (opt-in)
                self._values_enabled.setdefault(key, e.confirmed)

    def types(self) -> list[str]:
        return sorted(self._types_enabled)

    def values_for(self, etype: str) -> list[tuple[str, int]]:
        items = [(v, n) for (t, v), n in self._values_count.items() if t == etype]
        return sorted(items)

    def _cell_retained(self, r: int, c: int) -> list[Entity]:
        if not self._columns_enabled.get(c, False):
            return []
        if (r, c) in self._cells_excluded:
            return []
        out = []
        for e in self._cells.get((r, c), []):
            if not self._types_enabled.get(e.type, True):
                continue
            if not self._values_enabled.get((e.type, e.value), True):
                continue
            out.append(e)
        return out

    def count_retained(self, etype: str) -> int:
        total = 0
        for (r, c) in self._cells:
            total += sum(1 for e in self._cell_retained(r, c) if e.type == etype)
        return total
