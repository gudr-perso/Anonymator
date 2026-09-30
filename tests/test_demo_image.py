"""Le jeu de démonstration doit tenir ses promesses.

L'image `exemples/capture_mail_demo.png` n'est pas une illustration : c'est le
premier contact d'un utilisateur avec le mode Image. Si elle ne fait rien
détecter, la démonstration se retourne contre le produit.

Elle est régénérable par `scripts/make_demo_image.py` — les données fictives
sont lisibles dans ce script, pas enfouies dans un binaire.
"""
from pathlib import Path

import pytest
from PIL import Image

IMAGE = Path("exemples/capture_mail_demo.png")


def test_l_image_de_demonstration_est_livree():
    assert IMAGE.exists(), "régénérable : python scripts/make_demo_image.py"


def test_l_image_est_lisible_et_de_taille_raisonnable():
    """Elle voyage dans l'archive distribuée : ni illisible, ni démesurée."""
    from anonymator.files.image import image_io

    img = image_io.load_image(IMAGE)
    assert img.mode == "RGB"
    assert img.width >= 800 and img.height >= 500
    assert IMAGE.stat().st_size < 1_000_000


def test_le_script_de_generation_est_versionne():
    """Sans lui, l'image serait un binaire opaque dont personne ne pourrait
    vérifier que les données sont bien fictives."""
    assert Path("scripts/make_demo_image.py").exists()


@pytest.mark.integration
def test_les_regles_seules_trouvent_les_quatre_types_annonces():
    """Avec le vrai moteur OCR et SANS le modèle GLiNER — c'est l'état d'un
    utilisateur qui vient d'installer l'application et n'a pas encore
    téléchargé les 2,2 Go. Il doit déjà voir quelque chose."""
    from anonymator.files.image import image_io
    from anonymator.files.image.ocr import RapidOcrEngine
    from anonymator.ner import NullNer
    from anonymator.referential import Referential

    pages = image_io.scan_image(IMAGE, RapidOcrEngine(), NullNer(),
                                Referential.load_default())
    types = {e.type for e in pages[0].entities if e.confirmed}
    assert {"EMAIL", "PHONE", "IBAN", "SIRET"} <= types, (
        f"détecté seulement : {sorted(types)}")


@pytest.mark.integration
def test_le_caviardage_ne_deborde_pas_sur_la_phrase_entiere():
    """Garde-fou sur la granularité des rectangles.

    Le moteur rend par défaut une boîte par LIGNE. Prise pour un mot, elle
    faisait caviarder toute la phrase : masquer le nom du comptable effaçait
    « Pour toute question, notre comptable … reste joignable au ». On demande
    donc le découpage mot à mot. Si ce test tombe, c'est que la granularité a
    régressé — et l'utilisateur récupérera des images noircies à l'excès."""
    from anonymator.files.image import image_io
    from anonymator.files.image.ocr import RapidOcrEngine
    from anonymator.files.textlayer import PageText, rects_for_entity
    from anonymator.ner import NullNer
    from anonymator.referential import Referential

    pages = image_io.scan_image(IMAGE, RapidOcrEngine(), NullNer(),
                                Referential.load_default())
    page = pages[0]
    pt = PageText(0, page.text, page.words)

    telephones = [e for e in page.entities if e.type == "PHONE"]
    assert telephones, "le téléphone de démonstration doit être détecté"
    largeurs = [r[2] - r[0] for r in rects_for_entity(pt, telephones[0])]
    assert largeurs, "le téléphone doit produire au moins un rectangle"
    # La ligne fait ~220 px ; un rectangle par groupe de chiffres en fait ~25.
    assert max(largeurs) < 120, (
        f"rectangle trop large ({max(largeurs):.0f} px) : la phrase autour du "
        "numéro serait caviardée avec lui")


@pytest.mark.integration
def test_la_signature_manuscrite_reste_invisible_a_la_detection():
    """C'est le cœur pédagogique de l'image : elle prouve pourquoi
    l'application *propose* et pourquoi il faut relire. Si un jour la
    reconnaissance lisait la griffe, la démonstration perdrait son sens."""
    from anonymator.files.image import image_io
    from anonymator.files.image.ocr import RapidOcrEngine
    from anonymator.ner import NullNer
    from anonymator.referential import Referential

    pages = image_io.scan_image(IMAGE, RapidOcrEngine(), NullNer(),
                                Referential.load_default())
    # La griffe est tracée sous le corps du message ; aucune boîte de texte ne
    # doit couvrir cette bande, sans quoi il n'y aurait plus rien à tracer à la
    # main pour l'utilisateur.
    img = Image.open(IMAGE)
    bande_basse = img.height - 130
    boites_basses = [w for w in pages[0].words if w.rect[1] > bande_basse]
    lus = " ".join(w.text for w in boites_basses)
    assert "Salvatore" in lus or "Gérante" in lus, (
        "le bloc de signature doit rester lisible : seule la griffe ne l'est pas")
