# anonymator/files/pdf/redact.py
from pathlib import Path
import fitz

Rect = tuple[float, float, float, float]


def redact_page(page: "fitz.Page", rects: list[Rect]) -> None:
    """Marque chaque rectangle pour rédaction puis applique — destruction réelle
    du texte dans le flux du PDF (pas un simple masque visuel)."""
    for r in rects:
        page.add_redact_annot(fitz.Rect(*r), fill=(0, 0, 0))
    page.apply_redactions()


def purge_metadata(doc: "fitz.Document") -> None:
    """Vide les métadonnées document et le bloc XML (XMP)."""
    doc.set_metadata({})
    try:
        doc.del_xml_metadata()
    except Exception:   # noqa: BLE001 — absent sur certains PDF, sans gravité
        pass


def save_redacted(doc: "fitz.Document", out_path: Path) -> None:
    """Sauvegarde avec nettoyage (garbage collection des objets orphelins)."""
    doc.save(str(out_path), garbage=4, deflate=True, clean=True)
