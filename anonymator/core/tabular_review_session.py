"""Revue d'un tableau : entités rangées par cellule, arbitrages par colonne.

Les clés restent opaques — `(ligne, colonne)` pour un CSV, `(feuille, ligne,
colonne)` pour un classeur. Seule la sous-classe sait passer d'une cellule à sa
colonne et relire le contenu d'une colonne ; tout le reste est commun.

La classification automatique (cf. files/columns.py) reste le défaut. Un
forçage est un arbitrage explicite de l'utilisateur qui la recouvre pour une
colonne, sans la remplacer : revenir à AUTO rend la colonne à son plan."""

from anonymator.model import Entity
from anonymator.pipeline import detect_column
from anonymator.core.review_session_base import ReviewSessionBase

AUTO = "auto"      # le plan calculé par classify_columns fait foi
MASK = "mask"      # toutes les cellules non vides sont masquées
CLEAR = "clear"    # la colonne sort du périmètre


class TabularReviewSession(ReviewSessionBase):
    def __init__(self, scanned, ref, maskable_cols, plans=None):
        super().__init__(ref)
        self._cells = scanned
        self._columns_enabled = {c: True for c in maskable_cols}
        self.plans = dict(plans or {})
        self._overrides: dict[object, tuple[str, str | None]] = {}
        self._forced: dict[object, dict] = {}      # colonne -> {cellule: [Entity]}
        self._cells_excluded: set = set()
        self._all_keys: set = set()
        self._reindex()

    # --- à fournir par les sous-classes ---
    def column_of(self, cell_key):
        """Colonne à laquelle appartient une cellule."""
        raise NotImplementedError

    def column_values(self, col_key) -> dict:
        """{clé de cellule: texte} pour les lignes de données de la colonne."""
        raise NotImplementedError

    def has_column(self, col_key) -> bool:
        """La colonne existe-t-elle encore ? (report d'un override après
        réanalyse)"""
        raise NotImplementedError

    # --- plan et forçage ---
    def column_reason(self, col_key) -> str:
        """Pourquoi la colonne est traitée ainsi — texte prêt pour l'infobulle."""
        plan = self.plans.get(col_key)
        return plan.reason if plan else ""

    def default_type_for(self, col_key) -> str | None:
        """Type à proposer pour un forçage « tout anonymiser ».

        Un type déduit mais inactif (POSTAL_CODE, BIC, URL) ne produirait
        rien : mieux vaut ne rien proposer et laisser l'utilisateur choisir
        qu'offrir un forçage silencieusement sans effet."""
        plan = self.plans.get(col_key)
        etype = plan.etype if plan else None
        return etype if etype and self.ref.is_active(etype) else None

    def column_override(self, col_key) -> tuple[str, str | None]:
        return self._overrides.get(col_key, (AUTO, None))

    def column_overrides(self) -> dict:
        return dict(self._overrides)

    def set_column_override(self, col_key, mode: str,
                            etype: str | None = None) -> None:
        """AUTO rend la colonne à son plan ; MASK fabrique une entité couvrant
        chaque cellule non vide (même chemin que la politique TYPED, cf.
        pipeline.detect_column) ; CLEAR la sort du périmètre."""
        if mode == MASK and etype is None:
            raise ValueError("un forçage « tout anonymiser » exige un type")
        self._forced.pop(col_key, None)
        if mode == AUTO:
            self._overrides.pop(col_key, None)
        else:
            self._overrides[col_key] = (mode, etype)
        if mode == MASK:
            forced = {k: detect_column(v, etype, self.ref)
                      for k, v in self.column_values(col_key).items()}
            self._forced[col_key] = {k: v for k, v in forced.items() if v}
        self._reindex()

    def _reindex(self) -> None:
        groups = list(self._cells.values())
        keys = set(self._cells)
        for cells in self._forced.values():
            groups.extend(cells.values())
            keys |= set(cells)
        self._all_keys = keys
        self._index(groups)

    # --- lecture ---
    def _keys(self):
        return self._all_keys

    def _retained(self, cell_key) -> list[Entity]:
        col = self.column_of(cell_key)
        mode, _etype = self._overrides.get(col, (AUTO, None))
        if mode == CLEAR:
            return []
        if mode == MASK:
            return self._kept(self._forced.get(col, {}).get(cell_key, []))
        if not self._columns_enabled.get(col, False):
            return []
        if cell_key in self._cells_excluded:
            return []
        return self._kept(self._cells.get(cell_key, []))

    def _pending_at(self, cell_key) -> list[Entity]:
        col = self.column_of(cell_key)
        mode, _etype = self._overrides.get(col, (AUTO, None))
        if mode != AUTO:
            return []          # la colonne est tranchée : plus rien à signaler
        if not self._columns_enabled.get(col, False):
            return []
        if cell_key in self._cells_excluded:
            return []
        return self._pending(self._cells.get(cell_key, []))

    def retained_by_cell(self) -> dict:
        """{clé de cellule: entités retenues} — les cellules vides sont écartées."""
        out = {k: self._retained(k) for k in self._keys()}
        return {k: v for k, v in out.items() if v}

    # --- écriture ---
    def set_column_enabled(self, col_key, enabled: bool) -> None:
        self._columns_enabled[col_key] = enabled

    def set_cell_excluded(self, cell_key, excluded: bool) -> None:
        if excluded:
            self._cells_excluded.add(cell_key)
        else:
            self._cells_excluded.discard(cell_key)
