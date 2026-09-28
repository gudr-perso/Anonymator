# anonymator/files/image/image_io.py
"""Entrées/sorties image : décodage, orientation, purge des métadonnées.

Ce module ne connaît ni le NER ni le référentiel — uniquement les pixels."""
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

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
