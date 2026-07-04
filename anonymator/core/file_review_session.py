from anonymator.model import Entity
from anonymator.anonymize import apply_masking
from anonymator.report.audit import AuditReport


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
        self._values_confirmed: dict[tuple[str, str], bool] = {}
        self._cells_excluded: set[tuple[int, int]] = set()
        for ents in self._cells.values():
            for e in ents:
                self._types_enabled.setdefault(e.type, True)
                key = (e.type, e.value)
                self._values_count[key] = self._values_count.get(key, 0) + 1
                # défaut : confirmé → activé ; non confirmé → désactivé (opt-in)
                self._values_enabled.setdefault(key, e.confirmed)
                # non confirmé si une occurrence échoue au contrôle de la clé
                self._values_confirmed[key] = (
                    self._values_confirmed.get(key, True) and e.confirmed)

    def types(self) -> list[str]:
        return sorted(self._types_enabled)

    def total_occurrences(self) -> int:
        """Nombre total d'occurrences détectées (toutes valeurs, tous types)."""
        return sum(self._values_count.values())

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

    # --- setters ---
    def is_type_enabled(self, etype: str) -> bool:
        return self._types_enabled.get(etype, True)

    def set_type_enabled(self, etype: str, enabled: bool) -> None:
        self._types_enabled[etype] = enabled

    def set_value_enabled(self, etype: str, value: str, enabled: bool) -> None:
        self._values_enabled[(etype, value)] = enabled

    def set_column_enabled(self, col: int, enabled: bool) -> None:
        self._columns_enabled[col] = enabled

    def set_cell_excluded(self, r: int, c: int, excluded: bool) -> None:
        if excluded:
            self._cells_excluded.add((r, c))
        else:
            self._cells_excluded.discard((r, c))

    def entities_for_cell(self, r: int, c: int) -> list[Entity]:
        """Entités actuellement retenues pour la cellule (pilote le surlignage)."""
        return self._cell_retained(r, c)

    def unconfirmed_for_cell(self, r: int, c: int) -> list[Entity]:
        """Entités de la cellule au format valide mais clé invalide, décochées
        par défaut : à surligner distinctement (non masquées, opt-in). Exclut
        les cochées, les types désactivés, colonne exclue ou cellule exclue."""
        if not self._columns_enabled.get(c, False) or (r, c) in self._cells_excluded:
            return []
        out = []
        for e in self._cells.get((r, c), []):
            if not self._types_enabled.get(e.type, True):
                continue
            if e.confirmed or self._values_enabled.get((e.type, e.value), True):
                continue
            out.append(e)
        return out

    def is_value_enabled(self, etype: str, value: str) -> bool:
        """État de la case d'une valeur distincte (pour cocher l'UI)."""
        return self._values_enabled.get((etype, value), True)

    def is_value_confirmed(self, etype: str, value: str) -> bool:
        """Faux = format reconnu mais contrôle de la clé (checksum) échoué."""
        return self._values_confirmed.get((etype, value), True)

    # --- producteurs ---
    def masked_document(self):
        import copy
        out = copy.deepcopy(self.doc)
        for (r, c) in self._cells:
            ents = self._cell_retained(r, c)
            if ents:
                out.rows[r][c] = apply_masking(out.rows[r][c], ents, self.ref)
        return out

    def report(self) -> AuditReport:
        from anonymator.files.anonymize_file import _column_label
        rep = AuditReport()
        for (r, c) in self._cells:
            for e in self._cell_retained(r, c):
                location = f"{_column_label(self.doc, c)} L{r + 1}"
                rep.add(e.type, e.value, self.ref.tag_for(e.type), location)
        return rep
