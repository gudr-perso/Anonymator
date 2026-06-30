from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from anonymator.ner import NerDetector
from anonymator.referential import Referential
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
    ents = detect(text, ner, ref)
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


def anonymize_csv(path: Path, ner: NerDetector, ref: Referential,
                  output_dir: Path, when: datetime,
                  include: set[int] | None = None,
                  exclude: set[int] | None = None) -> FileResult:
    doc = csv_io.read_csv(path)
    cols = set(include) if include is not None else default_maskable_columns(
        doc.rows, doc.has_header)
    if exclude:
        cols -= set(exclude)

    data_start = 1 if doc.has_header else 0
    values = [doc.rows[r][c]
              for r in range(data_start, len(doc.rows))
              for c in cols if c < len(doc.rows[r])]
    cache = detect_unique(values, lambda v: detect(v, ner, ref))

    report = AuditReport()
    for r in range(data_start, len(doc.rows)):
        for c in cols:
            if c >= len(doc.rows[r]):
                continue
            original = doc.rows[r][c]
            ents = cache.get(original, [])
            if not ents:
                continue
            location = f"{_column_label(doc, c)} L{r + 1}"
            for e in ents:
                report.add(e.type, e.value, ref.tag_for(e.type), location)
            doc.rows[r][c] = apply_masking(original, ents, ref)

    out = anonymized_path(path, output_dir, when)
    csv_io.write_csv(doc, out)
    return FileResult(out, report)
