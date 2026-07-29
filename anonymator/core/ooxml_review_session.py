from anonymator.model import Entity
from anonymator.files.ooxml import scan
from anonymator.core.review_session_base import ReviewSessionBase


class OoxmlReviewSession(ReviewSessionBase):
    """État de revue d'un document docx/pptx (non-Qt). Contrôle à deux
    niveaux combinés en ET : type activé, valeur distincte activée. Miroir de
    FileReviewSession sans la dimension colonnes/cellules (clé = index d'unité).

    En mode revue, l'arbre couvre les entités des parties principales ;
    commentaires/notes docx et métadonnées sont traités par `post_fn`
    (entités confirmées) au moment de l'application."""

    def __init__(self, units, scanned: dict[int, list[Entity]], ref,
                 save_fn, post_fn):
        super().__init__(ref)
        self._units = units
        self._scanned = scanned
        self._save_fn = save_fn
        self._post_fn = post_fn
        self._index(scanned.values())

    # --- lecture ---
    def _keys(self):
        return self._scanned.keys()

    def _retained(self, i: int) -> list[Entity]:
        return self._kept(self._scanned.get(i, []))

    def entities_for_unit(self, i: int) -> list[Entity]:
        return self._retained(i)

    def unconfirmed_for_unit(self, i: int) -> list[Entity]:
        """Entités de l'unité au format valide mais clé invalide, décochées par
        défaut : à surligner distinctement (non masquées, opt-in)."""
        return self._pending(self._scanned.get(i, []))

    # --- production ---
    def apply_and_save(self, out_path):
        retained = {i: self._retained(i) for i in self._scanned}
        retained = {i: v for i, v in retained.items() if v}
        report = scan.apply_units(self._units, retained, self.ref)
        self._save_fn(out_path)
        self._post_fn(out_path, report)
        return report
