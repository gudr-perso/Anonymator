# anonymator/files/pdf/render.py
import fitz

RENDER_ZOOM = 2.0   # 1 point PDF = RENDER_ZOOM pixels dans l'image rendue


def render_page(page: "fitz.Page", zoom: float = RENDER_ZOOM) -> bytes:
    """Rend la page en image PNG (octets). Pas de Qt ici : la conversion en
    QPixmap se fait dans la couche UI (PdfCanvas)."""
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    return pix.tobytes("png")
