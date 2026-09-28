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
