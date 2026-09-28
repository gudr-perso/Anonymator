# anonymator/files/image/image_io.py
"""Entrées/sorties image : décodage, orientation, purge des métadonnées, plus
l'orchestration analyse/caviardage — miroir de `files/pdf/pdf_io.py`.

Les primitives de bas niveau (`load_image`, `strip_metadata`, `save_image`) ne
connaissent ni le NER ni le référentiel : uniquement les pixels."""
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from anonymator.core.chunking import detect_long
from anonymator.files.image.layout import page_from_boxes
from anonymator.files.image.redact import redact_image
from anonymator.files.textlayer import PageScan
from anonymator.ner import NerDetector
from anonymator.output_naming import anonymized_path
from anonymator.referential import Referential

Rect = tuple[float, float, float, float]

SUPPORTED_SUFFIXES = frozenset(
    {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"})


class UnsupportedImageFormat(Exception):
    pass


class CorruptImageError(Exception):
    pass


def load_image(path: Path) -> Image.Image:
    """Décode l'image, applique l'orientation EXIF et normalise en RGB.

    L'orientation est APPLIQUÉE ici, avant toute purge : purger d'abord ferait
    ressortir l'image tournée, puisque le visualiseur n'aurait plus le tag pour
    la redresser.

    D'une image animée, seule la première vue est lue — c'est celle que
    l'utilisateur voit et croit anonymiser."""
    if path.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise UnsupportedImageFormat(
            f"Format non supporté : {path.suffix}. "
            f"Formats acceptés : {', '.join(sorted(SUPPORTED_SUFFIXES))}")
    try:
        img = Image.open(path)
        img.load()
    except UnidentifiedImageError as exc:
        raise CorruptImageError("Image illisible ou endommagée") from exc
    except OSError as exc:
        raise CorruptImageError("Image illisible ou endommagée") from exc
    return ImageOps.exif_transpose(img).convert("RGB")


def strip_metadata(img: Image.Image) -> Image.Image:
    """Rend une copie ne portant que les pixels : ni EXIF, ni ICC, ni commentaire.

    On reconstruit l'image depuis son tampon brut — recopier l'objet Pillow
    traînerait son dictionnaire `info`."""
    return Image.frombytes(img.mode, img.size, img.tobytes())


def save_image(img: Image.Image, out_path: Path) -> Path:
    """Écrit l'image sans aucune métadonnée. L'original n'est jamais modifié."""
    clean = strip_metadata(img)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    clean.save(out_path)
    return out_path


# --- orchestration (miroir de pdf_io.scan_pdf / anonymize_pdf_redact) ---

def scan_image(path: Path, ocr, ner: NerDetector,
               ref: Referential) -> list[PageScan]:
    """Lit l'image, reconstruit sa couche de texte et y détecte les entités.

    Rend une liste d'une seule page, pour que la session de revue spatiale —
    écrite pour le PDF multi-pages — s'applique sans cas particulier.

    Lève UnsupportedImageFormat / CorruptImageError."""
    img = load_image(path)
    page = page_from_boxes(ocr.read(img))
    entities = detect_long(page.text, ner, ref)
    return [PageScan(page.page_index, page.text, page.words, entities)]


def anonymize_image_redact(path: Path, rects: list[Rect], output_dir: Path,
                           when: datetime) -> Path:
    """Caviarde les rectangles retenus, purge les métadonnées, enregistre.
    L'original n'est jamais modifié."""
    img = load_image(path)
    out = anonymized_path(path, output_dir, when)
    return save_image(redact_image(img, rects), out)
