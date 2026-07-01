# anonymator/files/pdf/pdf_io.py
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from anonymator.ner import NerDetector
from anonymator.referential import Referential
from anonymator.model import Entity
from anonymator.pipeline import detect
from anonymator.anonymize import apply_masking
from anonymator.report.audit import AuditReport
from anonymator.output_naming import anonymized_path
from anonymator.files import txt_io
from anonymator.files.anonymize_file import FileResult
from anonymator.files.pdf import extract, redact, render, propagate
from anonymator.files.pdf.extract import WordBox

Rect = tuple[float, float, float, float]


@dataclass
class PageScan:
    page_index: int
    text: str
    words: list[WordBox]
    entities: list[Entity]


def scan_pdf(path: Path, ner: NerDetector, ref: Referential) -> list[PageScan]:
    """Extrait chaque page (texte plat + boîtes) et détecte les entités.
    Lève ScannedPdfNotSupported / EncryptedPdfError / CorruptPdfError."""
    doc = extract.open_document(path)
    try:
        extract.ensure_native(doc)
        pages = extract.extract_pages(doc)
    finally:
        doc.close()
    per_page = [detect(pt.text, ner, ref) for pt in pages]
    per_page = propagate.propagate_across_pages(pages, per_page)
    return [PageScan(pt.page_index, pt.text, pt.words, ents)
            for pt, ents in zip(pages, per_page)]


def anonymize_pdf_text(path: Path, ner: NerDetector, ref: Referential,
                       output_dir: Path, when: datetime) -> FileResult:
    """Mode extraction : texte plat de toutes les pages → pipeline texte → .txt."""
    doc = extract.open_document(path)
    try:
        extract.ensure_native(doc)
        pages = extract.extract_pages(doc)
    finally:
        doc.close()
    text = "\n\n".join(p.text for p in pages)
    ents = [e for e in detect(text, ner, ref) if e.confirmed]
    report = AuditReport()
    for e in ents:
        report.add(e.type, e.value, ref.tag_for(e.type), "pdf")
    masked = apply_masking(text, ents, ref)
    out = anonymized_path(path.with_suffix(".txt"), output_dir, when)
    txt_io.write_text(masked, "utf-8", out)
    return FileResult(out, report)


def anonymize_pdf_redact(path: Path, rects_by_page: dict[int, list[Rect]],
                         output_dir: Path, when: datetime) -> Path:
    """Mode rédaction : caviarde les rectangles retenus par page, purge les
    métadonnées, sauvegarde. L'original n'est jamais modifié."""
    doc = extract.open_document(path)
    try:
        for i, page in enumerate(doc):
            rects = rects_by_page.get(i, [])
            if rects:
                redact.redact_page(page, rects)
        redact.purge_metadata(doc)
        out = anonymized_path(path, output_dir, when)
        redact.save_redacted(doc, out)
    finally:
        doc.close()
    return out


def render_page_at(path: Path, page_index: int,
                   zoom: float = render.RENDER_ZOOM) -> bytes:
    """Rend une page en PNG (pour l'aperçu de revue)."""
    doc = extract.open_document(path)
    try:
        return render.render_page(doc[page_index], zoom=zoom)
    finally:
        doc.close()
