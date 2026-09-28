"""Tests du moteur OCR réel. Désélectionnés par défaut :

    .venv/Scripts/python -m pytest -m integration -q
"""
import socket
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

pytestmark = pytest.mark.integration

# Polices TrueType courantes selon la plateforme. La police bitmap par défaut
# de Pillow ne rend pas les accents : sans TTF, le test des accents n'aurait
# aucun sens et vaut mieux être sauté qu'être faux.
_POLICES = [
    "C:/Windows/Fonts/arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def _police(taille: int = 30):
    for chemin in _POLICES:
        if Path(chemin).exists():
            return ImageFont.truetype(chemin, taille)
    return None


def _image_avec_texte(texte: str) -> Image.Image:
    font = _police()
    if font is None:
        pytest.skip("aucune police TrueType disponible sur cette machine")
    img = Image.new("RGB", (760, 90), (255, 255, 255))
    ImageDraw.Draw(img).text((20, 28), texte, fill=(0, 0, 0), font=font)
    return img


def test_aucun_acces_reseau_pendant_un_ocr(monkeypatch):
    """Le socle promet « aucun appel réseau en usage normal ». On coupe la
    socket : si RapidOCR tente de résoudre un modèle en ligne, le test tombe.

    C'est le test qui protège la promesse produit — pas une formalité."""
    def _interdit(*a, **k):
        raise AssertionError("acces reseau pendant l'OCR")

    monkeypatch.setattr(socket, "socket", _interdit)
    monkeypatch.setattr(socket, "create_connection", _interdit)

    from anonymator.files.image.ocr import RapidOcrEngine
    boxes = RapidOcrEngine().read(_image_avec_texte("Dupont"))
    assert any("upont" in b.text for b in boxes)


def test_les_accents_francais_sont_restitues():
    """Critère d'acceptation n°1 du banc de mesure (tâche 1), figé en test.

    Si ce test tombe un jour, c'est que le modèle de reconnaissance a changé :
    tout le choix du moteur repose sur ce résultat."""
    from anonymator.files.image.ocr import RapidOcrEngine
    boxes = RapidOcrEngine().read(
        _image_avec_texte("\u00c9l\u00e9onore Ch\u00e2teauneuf \u00e0 N\u00eemes"))
    lu = " ".join(b.text for b in boxes)
    assert "\u00c9l\u00e9onore" in lu
    assert "Ch\u00e2teauneuf" in lu
    assert "N\u00eemes" in lu


def test_une_photo_large_est_caviardee_aux_bonnes_coordonnees(tmp_path):
    """Bout en bout sur une image plus large que MAX_SIDE : si la remise à
    l'échelle était fausse, le caviardage tomberait à côté du texte."""
    from anonymator.files.image import image_io
    from anonymator.files.image.ocr import RapidOcrEngine
    from anonymator.files.textlayer import PageText, rects_for_entity
    from anonymator.ner import NullNer
    from anonymator.referential import Referential
    from datetime import datetime

    grande = _image_avec_texte("Contact : jean.dupre@exemple.fr").resize(
        (3040, 360))
    src = tmp_path / "large.png"
    grande.save(src)

    pages = image_io.scan_image(src, RapidOcrEngine(), NullNer(),
                                Referential.load_default())
    page = pages[0]
    emails = [e for e in page.entities if e.type == "EMAIL"]
    assert emails, f"aucun e-mail detecte dans {page.text!r}"

    pt = PageText(0, page.text, page.words)
    rects = rects_for_entity(pt, emails[0])
    out = image_io.anonymize_image_redact(src, rects, tmp_path,
                                          datetime(2026, 9, 28))
    relu = Image.open(out)
    for x0, y0, x1, y1 in rects:
        zone = relu.crop((int(x0), int(y0), int(x1), int(y1)))
        assert zone.getextrema() == ((0, 0), (0, 0), (0, 0))
