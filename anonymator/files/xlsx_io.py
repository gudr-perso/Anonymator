from datetime import datetime
from pathlib import Path
import openpyxl
from anonymator.ner import NerDetector
from anonymator.referential import Referential
from anonymator.pipeline import detect
from anonymator.anonymize import apply_masking
from anonymator.dedup import detect_unique
from anonymator.report.audit import AuditReport
from anonymator.output_naming import anonymized_path

def anonymize_workbook(path: Path, ner: NerDetector, ref: Referential,
                       output_dir: Path, when: datetime):
    wb = openpyxl.load_workbook(path)
    string_cells = []  # (sheet_title, coordinate, value)
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if cell.data_type == "s" and isinstance(cell.value, str):
                    string_cells.append((ws.title, cell.coordinate, cell.value))
    cache = detect_unique([v for _, _, v in string_cells],
                          lambda v: detect(v, ner, ref))
    report = AuditReport()
    for sheet_title, coord, value in string_cells:
        ents = cache.get(value, [])
        if not ents:
            continue
        location = f"{sheet_title}!{coord}"
        for e in ents:
            report.add(e.type, e.value, ref.tag_for(e.type), location)
        wb[sheet_title][coord] = apply_masking(value, ents, ref)
    out = anonymized_path(path, output_dir, when)
    wb.save(out)
    return out, report
