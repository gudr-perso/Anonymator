from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from anonymator.ner import NerDetector
from anonymator.referential import Referential
from anonymator.model import Entity
from anonymator.pipeline import detect
from anonymator.anonymize import apply_masking
from anonymator.dedup import detect_unique
from anonymator.report.audit import AuditReport
from anonymator.output_naming import anonymized_path
from anonymator.files import csv_io
from anonymator.files import txt_io
from anonymator.files import xlsx_io
from anonymator.files.columns import default_maskable_columns


@dataclass
class FileResult:
    output_path: Path
    report: AuditReport


def _column_label(doc, col: int) -> str:
    if doc.has_header and doc.rows and col < len(doc.rows[0]):
        return doc.rows[0][col]
    return f"col{col}"


def anonymize_txt(path: Path, ner: NerDetector, ref: Referential,
                  output_dir: Path, when: datetime) -> FileResult:
    text, encoding = txt_io.read_text(path)
    ents = [e for e in detect(text, ner, ref) if e.confirmed]   # direct : pas de non confirmé
    report = AuditReport()
    for e in ents:
        report.add(e.type, e.value, ref.tag_for(e.type), "texte")
    masked = apply_masking(text, ents, ref)
    out = anonymized_path(path, output_dir, when)
    txt_io.write_text(masked, encoding, out)
    return FileResult(out, report)


def anonymize_xlsx(path: Path, ner: NerDetector, ref: Referential,
                   output_dir: Path, when: datetime) -> FileResult:
    out, report = xlsx_io.anonymize_workbook(path, ner, ref, output_dir, when)
    return FileResult(out, report)


def anonymize_docx(path: Path, ner: NerDetector, ref: Referential,
                   output_dir: Path, when: datetime) -> FileResult:
    from anonymator.files.ooxml import docx_io
    out, report = docx_io.anonymize_document(path, ner, ref, output_dir, when)
    return FileResult(out, report)


def anonymize_pptx(path: Path, ner: NerDetector, ref: Referential,
                   output_dir: Path, when: datetime) -> FileResult:
    from anonymator.files.ooxml import pptx_io
    out, report = pptx_io.anonymize_document(path, ner, ref, output_dir, when)
    return FileResult(out, report)


def scan_csv(doc, ner: NerDetector, ref: Referential,
             cols: set[int]) -> dict[tuple[int, int], list[Entity]]:
    """Détecte les entités par cellule (dédupliqué) sur les colonnes `cols`.
    Clés = (ligne, colonne) ; valeurs = entités détectées dans la cellule.
    Offsets des entités relatifs à la valeur de cellule (cf. dedup.detect_unique)."""
    data_start = 1 if doc.has_header else 0
    values = [doc.rows[r][c]
              for r in range(data_start, len(doc.rows))
              for c in cols if c < len(doc.rows[r])]
    cache = detect_unique(values, lambda v: detect(v, ner, ref))
    result: dict[tuple[int, int], list[Entity]] = {}
    for r in range(data_start, len(doc.rows)):
        for c in cols:
            if c >= len(doc.rows[r]):
                continue
            ents = cache.get(doc.rows[r][c], [])
            if ents:
                result[(r, c)] = ents
    return result


def apply_csv(doc, retained_by_cell: dict[tuple[int, int], list[Entity]],
              ref: Referential) -> tuple["csv_io.CsvDocument", AuditReport]:
    """Masque les entités retenues par cellule et produit le rapport.
    Mute `doc.rows` en place et le retourne."""
    report = AuditReport()
    for (r, c), ents in retained_by_cell.items():
        if not ents:
            continue
        original = doc.rows[r][c]
        location = f"{_column_label(doc, c)} L{r + 1}"
        for e in ents:
            report.add(e.type, e.value, ref.tag_for(e.type), location)
        doc.rows[r][c] = apply_masking(original, ents, ref)
    return doc, report


def anonymize_csv(path: Path, ner: NerDetector, ref: Referential,
                  output_dir: Path, when: datetime,
                  include: set[int] | None = None,
                  exclude: set[int] | None = None) -> FileResult:
    doc = csv_io.read_csv(path)
    cols = set(include) if include is not None else default_maskable_columns(
        doc.rows, doc.has_header)
    if exclude:
        cols -= set(exclude)
    scanned = scan_csv(doc, ner, ref, cols)
    scanned = {k: [e for e in v if e.confirmed]      # direct : ignore les non confirmés
               for k, v in scanned.items()}
    scanned = {k: v for k, v in scanned.items() if v}
    doc, report = apply_csv(doc, scanned, ref)
    out = anonymized_path(path, output_dir, when)
    csv_io.write_csv(doc, out)
    return FileResult(out, report)


class UnsupportedFormat(Exception):
    pass


def anonymize_file(path: Path, ner: NerDetector, ref: Referential,
                   output_dir: Path, when: datetime,
                   include: set[int] | None = None,
                   exclude: set[int] | None = None) -> FileResult:
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return anonymize_txt(path, ner, ref, output_dir, when)
    if suffix == ".csv":
        return anonymize_csv(path, ner, ref, output_dir, when,
                             include=include, exclude=exclude)
    if suffix == ".xlsx":
        if include is not None or exclude is not None:
            raise NotImplementedError(
                "Sélection de colonnes non supportée pour .xlsx en v1")
        return anonymize_xlsx(path, ner, ref, output_dir, when)
    if suffix == ".docx":
        return anonymize_docx(path, ner, ref, output_dir, when)
    if suffix == ".pptx":
        return anonymize_pptx(path, ner, ref, output_dir, when)
    raise UnsupportedFormat(
        f"Format non supporté : {suffix} "
        f"(formats acceptés : .txt, .csv, .xlsx, .docx, .pptx)")
