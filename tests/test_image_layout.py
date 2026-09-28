from anonymator.files.image.layout import page_from_boxes
from anonymator.files.image.ocr import OcrBox


def test_boites_en_desordre_sont_remises_en_ordre_de_lecture():
    boxes = [
        OcrBox("monde", (60.0, 0.0, 110.0, 20.0), 0.9),
        OcrBox("suite", (0.0, 40.0, 50.0, 60.0), 0.9),
        OcrBox("Bonjour", (0.0, 0.0, 50.0, 20.0), 0.9),
    ]
    page = page_from_boxes(boxes)
    assert page.text == "Bonjour monde\nsuite"


def test_les_offsets_pointent_sur_le_bon_mot():
    boxes = [
        OcrBox("Jean", (0.0, 0.0, 40.0, 20.0), 0.9),
        OcrBox("Dupont", (45.0, 0.0, 100.0, 20.0), 0.9),
    ]
    page = page_from_boxes(boxes)
    assert page.text == "Jean Dupont"
    w = page.words[1]
    assert page.text[w.char_start:w.char_end] == "Dupont"
    assert w.rect == (45.0, 0.0, 100.0, 20.0)


def test_deux_lignes_sont_separees_par_un_saut_de_ligne():
    boxes = [
        OcrBox("haut", (0.0, 0.0, 40.0, 20.0), 0.9),
        OcrBox("bas", (0.0, 100.0, 40.0, 120.0), 0.9),
    ]
    assert page_from_boxes(boxes).text == "haut\nbas"


def test_boites_de_hauteurs_inegales_sur_la_meme_ligne_restent_groupees():
    # Un titre en gras et un mot plus petit alignés : chevauchement vertical
    # majoritaire -> même ligne.
    boxes = [
        OcrBox("TOTAL", (0.0, 0.0, 60.0, 30.0), 0.9),
        OcrBox("42", (70.0, 5.0, 90.0, 25.0), 0.9),
    ]
    assert page_from_boxes(boxes).text == "TOTAL 42"


def test_limite_connue_deux_colonnes_sont_lues_entrelacees():
    """Épingle une limite assumée : sans blocs (que l'OCR ne fournit pas), deux
    colonnes à la même hauteur forment une seule ligne. Les rectangles restent
    justes — le caviardage ne rate rien — mais le contexte offert à GLiNER est
    dégradé. Si ce test casse un jour, c'est que le regroupement a changé :
    vérifier que c'est voulu."""
    boxes = [
        OcrBox("Nom", (0.0, 0.0, 30.0, 20.0), 0.9),
        OcrBox("Adresse", (200.0, 0.0, 260.0, 20.0), 0.9),
        OcrBox("Jean", (0.0, 30.0, 30.0, 50.0), 0.9),
        OcrBox("Lyon", (200.0, 30.0, 260.0, 50.0), 0.9),
    ]
    assert page_from_boxes(boxes).text == "Nom Adresse\nJean Lyon"


def test_page_vide():
    page = page_from_boxes([])
    assert page.text == ""
    assert page.words == []
    assert page.page_index == 0
