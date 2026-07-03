from anonymator.model import Entity
from anonymator.pipeline import detect
from anonymator.dedup import detect_unique
from anonymator.report.audit import AuditReport
from anonymator.files.ooxml import run_remap
from anonymator.files.ooxml.text_unit import TextUnit


def scan_units(units: list[TextUnit], ner, ref) -> dict[int, list[Entity]]:
    """Détecte les entités par unité (dédupliqué). Clé = index d'unité.
    Offsets relatifs au texte de l'unité (cf. dedup.detect_unique)."""
    texts = [u.text() for u in units]
    cache = detect_unique(texts, lambda v: detect(v, ner, ref))
    result: dict[int, list[Entity]] = {}
    for i, u in enumerate(units):
        ents = cache.get(u.text(), [])
        if ents:
            result[i] = ents
    return result


def confirmed_only(scanned: dict[int, list[Entity]]) -> dict[int, list[Entity]]:
    kept = {i: [e for e in ents if e.confirmed] for i, ents in scanned.items()}
    return {i: v for i, v in kept.items() if v}


def apply_units(units: list[TextUnit], retained: dict[int, list[Entity]],
                ref, report: AuditReport | None = None) -> AuditReport:
    """Masque les entités retenues par unité et alimente le rapport.
    Mute les runs des unités en place. Réutilise un `report` existant si fourni."""
    report = report if report is not None else AuditReport()
    for i, ents in retained.items():
        if not ents:
            continue
        u = units[i]
        for e in ents:
            report.add(e.type, e.value, ref.tag_for(e.type), u.location)
        run_remap.apply(u.runs, ents, ref)
    return report
