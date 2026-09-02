from anonymator.model import Entity
from anonymator.report.audit import AuditReport
from anonymator.files import xlsx_io
from anonymator.files.columns import SKIP
from anonymator.core.tabular_review_session import TabularReviewSession


class XlsxReviewSession(TabularReviewSession):
    """État de revue d'un classeur (non-Qt). Clé de cellule = (feuille, ligne,
    colonne), clé de colonne = (feuille, colonne).

    Même contrôle que le CSV, une dimension de plus : une colonne s'entend
    toujours « colonne de telle feuille », deux feuilles n'ayant aucune raison
    de partager un plan."""

    def __init__(self, result: xlsx_io.XlsxScanResult, ref):
        self.result = result
        plans = {(sheet, col): plan
                 for sheet, sheet_plans in result.plans.items()
                 for col, plan in sheet_plans.items()}
        maskable = {k for k, p in plans.items() if p.policy != SKIP}
        super().__init__(result.scanned, ref, maskable, plans)

    # --- clés ---
    def column_of(self, cell_key):
        sheet, _r, col = cell_key
        return (sheet, col)

    def has_column(self, col_key) -> bool:
        sheet, col = col_key
        matrix = self.result.matrices.get(sheet)
        if not matrix:
            return False
        return 0 <= col < max((len(r) for r in matrix), default=0)

    def column_values(self, col_key) -> dict:
        sheet, col = col_key
        matrix = self.result.matrices.get(sheet, [])
        start = 1 if self.result.has_header.get(sheet) else 0
        return {(sheet, r, col): matrix[r][col]
                for r in range(start, len(matrix)) if col < len(matrix[r])}

    # --- adaptateurs de signature ---
    def entities_for_cell(self, sheet: str, r: int, c: int) -> list[Entity]:
        """Entités actuellement retenues pour la cellule (pilote le surlignage)."""
        return self._retained((sheet, r, c))

    def unconfirmed_for_cell(self, sheet: str, r: int, c: int) -> list[Entity]:
        """Entités au format valide mais clé invalide, décochées par défaut :
        à surligner distinctement (non masquées, opt-in)."""
        return self._pending_at((sheet, r, c))

    def set_cell_excluded(self, sheet: str, r: int, c: int,
                          excluded: bool) -> None:
        super().set_cell_excluded((sheet, r, c), excluded)

    # --- production ---
    def apply_and_save(self, out_path) -> AuditReport:
        """Écrit le classeur masqué et rend le rapport.

        Rejouable : `apply_workbook` rend d'abord aux cellules déjà masquées
        leur valeur d'origine, de sorte qu'un second enregistrement (après un
        décochage, par exemple) reparte du classeur intact."""
        report = xlsx_io.apply_workbook(self.result, self.retained_by_cell(),
                                        self.ref)
        xlsx_io.purge_metadata(self.result.workbook, report)
        self.result.workbook.save(out_path)
        return report
