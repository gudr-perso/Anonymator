from datetime import datetime

from PIL import Image

from anonymator.files.image.ocr import FakeOcr, NullOcr, OcrBox
from anonymator.ner import FakeNer
from anonymator.referential import Referential
from anonymator.ui.image_screen import ImageScreen
from anonymator.ui.model_loader import ModelLoader


class _Prefs:
    output_dir = ""


def _ecran(qtbot, boxes=()):
    screen = ImageScreen(Referential.load_default(), ModelLoader(FakeNer({})),
                         _Prefs(), on_back=lambda: None)
    screen.ocr_provider = lambda: FakeOcr(list(boxes))
    qtbot.addWidget(screen)
    return screen


def _image(tmp_path, nom="capture.png"):
    p = tmp_path / nom
    Image.new("RGB", (200, 100), (255, 255, 255)).save(p)
    return p


def _analyser(screen, qtbot, path):
    screen.load_path(str(path))
    screen.analyze()
    qtbot.waitUntil(lambda: screen.session is not None, timeout=10000)


def test_l_ecran_affiche_le_perimetre_image(qtbot):
    assert "manuscrit" in _ecran(qtbot).perimetre.rendered_text().lower()


def test_le_moteur_par_defaut_est_neutre(qtbot):
    """Aucun chargement de modèle à l'ouverture de l'écran : l'application
    doit rester instantanée."""
    assert isinstance(_ecran(qtbot).ocr_provider(), (FakeOcr, NullOcr))


def test_apres_analyse_les_entites_sont_listees(qtbot, tmp_path):
    screen = _ecran(qtbot, [OcrBox("jean@exemple.fr", (0.0, 0.0, 120.0, 20.0), 0.9)])
    _analyser(screen, qtbot, _image(tmp_path))
    assert screen.session.types() == ["EMAIL"]


def test_une_zone_tracee_a_la_main_est_retenue(qtbot, tmp_path):
    screen = _ecran(qtbot)
    _analyser(screen, qtbot, _image(tmp_path))
    screen._on_manual_rect((5.0, 5.0, 25.0, 25.0))
    assert screen.session.manual_rects(0) == [(5.0, 5.0, 25.0, 25.0)]


def test_l_enregistrement_produit_une_image_caviardee(qtbot, tmp_path):
    screen = _ecran(qtbot)
    _analyser(screen, qtbot, _image(tmp_path))
    screen._on_manual_rect((10.0, 10.0, 40.0, 40.0))
    out = screen.run_redact(tmp_path / "sortie", datetime(2026, 9, 28, 14, 0, 0))
    assert out.name == "capture_ano_20260928140000.png"
    assert Image.open(out).crop((10, 10, 40, 40)).getextrema() == (
        (0, 0), (0, 0), (0, 0))


def test_sans_analyse_l_enregistrement_ne_produit_rien(qtbot, tmp_path):
    """La revue est obligatoire : aucun chemin ne mène à un fichier de sortie
    sans être passé par elle."""
    screen = _ecran(qtbot)
    screen.load_path(str(_image(tmp_path)))
    assert screen.run_redact(tmp_path / "sortie") is None


def test_un_format_non_supporte_affiche_un_message_sans_planter(qtbot, tmp_path):
    p = tmp_path / "photo.heic"
    p.write_bytes(b"pas une image")
    screen = _ecran(qtbot)
    screen.load_path(str(p))
    assert "Format non supporté" in screen.meta_label.text()
    assert screen.session is None


def test_l_ecran_signale_l_attente_pendant_l_analyse(qtbot, tmp_path):
    """4,4 s mesurées sur une image nette : sans retour visuel, l'utilisateur
    croit l'application figée."""
    screen = _ecran(qtbot)
    screen.show()          # isVisible() d'un enfant est faux si le parent est caché
    assert not screen._overlay.isVisible()
    screen._set_busy(True)
    assert screen._overlay.isVisible()
    assert not screen.btn_review.isEnabled()
    screen._set_busy(False)
    assert not screen._overlay.isVisible()
    assert screen.btn_review.isEnabled()


# --- valeurs a cle de controle fausse ---------------------------------------
# Meme comportement que le PDF, le mode Fichier et le mode Texte : surlignage
# en pointille, mention explicite dans la liste, et case DECOCHEE par defaut.
# C'est le comportement le plus deroutant de l'outil ; il ne doit pas differer
# d'un ecran a l'autre.

_IBAN_CLE_FAUSSE = "FR76 3000 6000 0112 3456 7890 188"


def _ecran_cle_fausse(qtbot, tmp_path):
    screen = _ecran(qtbot, [OcrBox(_IBAN_CLE_FAUSSE, (10.0, 10.0, 200.0, 30.0), 0.9)])
    _analyser(screen, qtbot, _image(tmp_path))
    return screen


def test_une_cle_fausse_porte_la_mention_dans_la_liste(qtbot, tmp_path):
    screen = _ecran_cle_fausse(qtbot, tmp_path)
    libelles = []
    for i in range(screen.side.topLevelItemCount()):
        parent = screen.side.topLevelItem(i)
        libelles += [parent.child(j).text(0) for j in range(parent.childCount())]
    assert any("clé non conforme" in t for t in libelles), libelles


def test_une_cle_fausse_est_decochee_par_defaut(qtbot, tmp_path):
    from PySide6.QtCore import Qt
    screen = _ecran_cle_fausse(qtbot, tmp_path)
    parent = screen.side.topLevelItem(0)
    assert parent.child(0).checkState(0) == Qt.Unchecked


def test_cocher_une_cle_fausse_la_fait_masquer(qtbot, tmp_path):
    """La valeur brute doit survivre a la decoration du libelle : sans cela,
    cocher la case ne retrouverait aucune entite."""
    from PySide6.QtCore import Qt
    screen = _ecran_cle_fausse(qtbot, tmp_path)
    assert screen.session.retained_rects_by_page().get(0, []) == []
    parent = screen.side.topLevelItem(0)
    parent.child(0).setCheckState(0, Qt.Checked)
    assert screen.session.retained_rects_by_page().get(0, []) != []


def test_la_cle_fausse_est_transmise_au_canevas_en_pointille(qtbot, tmp_path):
    screen = _ecran_cle_fausse(qtbot, tmp_path)
    assert screen.session.unconfirmed_entity_rects(0) != []
    assert screen.session.retained_entity_rects(0) == []
