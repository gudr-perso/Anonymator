# anonymator/core/pdf_review_session.py
from dataclasses import dataclass
from anonymator.model import Entity
from anonymator.report.audit import AuditReport
from anonymator.files.pdf import mapping
from anonymator.files.pdf.extract import PageText
from anonymator.files.pdf.pdf_io import PageScan

Rect = tuple[float, float, float, float]
_MANUAL_TYPE = "ZONE"
_MANUAL_TAG = "[ZONE]"


@dataclass
class _Occ:
    page: int
    entity: Entity
    rects: list[Rect]


class PdfReviewSession:
    """État de revue d'un PDF (non-Qt). Miroir de FileReviewSession, indexé par
    (page, rect). Trois niveaux combinés en ET : type activé, valeur distincte
    activée, occurrence non exclue individuellement. Plus des rects manuels."""

    def __init__(self, pages: list[PageScan], ref):
        self.ref = ref
        self._occs: list[_Occ] = []
        self._types_enabled: dict[str, bool] = {}
        self._values_enabled: dict[tuple[str, str], bool] = {}
        self._values_count: dict[tuple[str, str], int] = {}
        self._excluded: set[int] = set()                 # indices dans self._occs
        self._manual: dict[int, list[Rect]] = {}
        for ps in pages:
            page_text = PageText(ps.page_index, ps.text, ps.words)
            for e in ps.entities:
                rects = mapping.rects_for_entity(page_text, e)
                self._occs.append(_Occ(ps.page_index, e, rects))
                self._types_enabled.setdefault(e.type, True)
                key = (e.type, e.value)
                self._values_count[key] = self._values_count.get(key, 0) + 1
                self._values_enabled.setdefault(key, e.confirmed)

    # --- lecture (API identique à FileReviewSession) ---
    def types(self) -> list[str]:
        return sorted(self._types_enabled)

    def total_occurrences(self) -> int:
        return sum(self._values_count.values())

    def values_for(self, etype: str) -> list[tuple[str, int]]:
        items = [(v, n) for (t, v), n in self._values_count.items() if t == etype]
        return sorted(items)

    def _occ_retained(self, i: int) -> bool:
        occ = self._occs[i]
        if i in self._excluded:
            return False
        if not self._types_enabled.get(occ.entity.type, True):
            return False
        if not self._values_enabled.get((occ.entity.type, occ.entity.value), True):
            return False
        return True

    def count_retained(self, etype: str) -> int:
        return sum(1 for i, occ in enumerate(self._occs)
                   if occ.entity.type == etype and self._occ_retained(i))

    def is_type_enabled(self, etype: str) -> bool:
        return self._types_enabled.get(etype, True)

    def is_value_enabled(self, etype: str, value: str) -> bool:
        return self._values_enabled.get((etype, value), True)

    # --- écriture ---
    def set_type_enabled(self, etype: str, enabled: bool) -> None:
        self._types_enabled[etype] = enabled

    def set_value_enabled(self, etype: str, value: str, enabled: bool) -> None:
        self._values_enabled[(etype, value)] = enabled

    def set_occurrence_excluded(self, page: int, occ_index: int, excluded: bool) -> None:
        """Exclut une occurrence individuelle. occ_index = index dans occurrences()."""
        if excluded:
            self._excluded.add(occ_index)
        else:
            self._excluded.discard(occ_index)

    # --- rects manuels ---
    def add_manual_rect(self, page: int, rect: Rect) -> None:
        self._manual.setdefault(page, []).append(rect)

    def manual_rects(self, page: int) -> list[Rect]:
        return list(self._manual.get(page, []))

    def clear_manual_rects(self, page: int) -> None:
        self._manual.pop(page, None)

    # --- producteurs ---
    def occurrences(self, page: int) -> list[tuple[int, Entity]]:
        """(occ_index global, entité) des occurrences de la page — pour l'UI."""
        return [(i, occ.entity) for i, occ in enumerate(self._occs)
                if occ.page == page]

    def retained_entity_rects(self, page: int) -> list[tuple[Rect, str]]:
        """(rect, type) des entités retenues sur la page (overlays colorés)."""
        out: list[tuple[Rect, str]] = []
        for i, occ in enumerate(self._occs):
            if occ.page == page and self._occ_retained(i):
                for r in occ.rects:
                    out.append((r, occ.entity.type))
        return out

    def retained_rects_by_page(self) -> dict[int, list[Rect]]:
        """Tous les rectangles à caviarder par page (entités retenues + manuels)."""
        result: dict[int, list[Rect]] = {}
        for i, occ in enumerate(self._occs):
            if self._occ_retained(i):
                result.setdefault(occ.page, []).extend(occ.rects)
        for page, rects in self._manual.items():
            result.setdefault(page, []).extend(rects)
        return result

    def report(self) -> AuditReport:
        rep = AuditReport()
        for i, occ in enumerate(self._occs):
            if self._occ_retained(i):
                rep.add(occ.entity.type, occ.entity.value,
                        self.ref.tag_for(occ.entity.type), f"page {occ.page + 1}")
        for page, rects in self._manual.items():
            for _r in rects:
                rep.add(_MANUAL_TYPE, "(zone manuelle)", _MANUAL_TAG,
                        f"page {page + 1}")
        return rep
