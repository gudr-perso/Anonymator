from anonymator.model import Entity
from anonymator.anonymize import apply_masking
from anonymator.report.audit import AuditReport
from anonymator.core.tabular_review_session import TabularReviewSession


class FileReviewSession(TabularReviewSession):
    """État de revue d'un fichier CSV (non-Qt). Clé de cellule = (ligne, colonne).

    Cinq niveaux de contrôle : l'arbitrage de colonne (auto / tout anonymiser /
    tout libérer) l'emporte sur les quatre autres, combinés en ET — colonne
    incluse, type activé, valeur distincte activée, cellule non exclue
    individuellement. Une valeur démarre activée si ses entités sont
    `confirmed`, désactivée sinon (opt-in)."""

    def __init__(self, doc, scanned: dict[tuple[int, int], list[Entity]],
                 ref, maskable_cols: set[int], plans=None):
        self.doc = doc
        super().__init__(scanned, ref, maskable_cols, plans)

    # --- clés ---
    def column_of(self, cell_key):
        return cell_key[1]

    def has_column(self, col_key) -> bool:
        return 0 <= col_key < max((len(r) for r in self.doc.rows), default=0)

    def column_values(self, col_key) -> dict:
        start = 1 if self.doc.has_header else 0
        return {(r, col_key): self.doc.rows[r][col_key]
                for r in range(start, len(self.doc.rows))
                if col_key < len(self.doc.rows[r])}

    # --- adaptateurs de signature (r, c) ---
    def set_cell_excluded(self, r: int, c: int, excluded: bool) -> None:
        super().set_cell_excluded((r, c), excluded)

    def entities_for_cell(self, r: int, c: int) -> list[Entity]:
        """Entités actuellement retenues pour la cellule (pilote le surlignage)."""
        return self._retained((r, c))

    def unconfirmed_for_cell(self, r: int, c: int) -> list[Entity]:
        """Entités de la cellule au format valide mais clé invalide, décochées
        par défaut : à surligner distinctement (non masquées, opt-in)."""
        return self._pending_at((r, c))

    # --- producteurs ---
    def masked_document(self):
        import copy
        out = copy.deepcopy(self.doc)
        for (r, c), ents in self.retained_by_cell().items():
            out.rows[r][c] = apply_masking(out.rows[r][c], ents, self.ref)
        return out

    def report(self) -> AuditReport:
        from anonymator.files.anonymize_file import _column_label
        rep = AuditReport()
        for (r, c), ents in self.retained_by_cell().items():
            location = f"{_column_label(self.doc, c)} L{r + 1}"
            for e in ents:
                rep.add(e.type, e.value, self.ref.tag_for(e.type), location)
        return rep

    def apply_and_save(self, out_path) -> AuditReport:
        """Écrit le CSV masqué et rend le rapport. Même contrat que
        OoxmlReviewSession.apply_and_save : l'écran n'a plus à savoir de quel
        format relève la session qu'il tient."""
        from anonymator.files import csv_io
        report = self.report()
        csv_io.write_csv(self.masked_document(), out_path)
        return report
