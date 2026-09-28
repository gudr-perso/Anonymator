from anonymator.files.image.ocr import NullOcr
from anonymator.ui.main_window import MainWindow


def test_l_accueil_propose_une_tuile_image(qtbot):
    from PySide6.QtWidgets import QLabel
    w = MainWindow()
    qtbot.addWidget(w)
    libelles = [lbl.text().lower()
                for lbl in w.home.btn_image.findChildren(QLabel)]
    assert any("image" in t for t in libelles)


def test_un_clic_sur_la_tuile_ouvre_l_ecran_image(qtbot):
    """Teste le câblage réel, pas seulement la méthode de navigation."""
    w = MainWindow()
    qtbot.addWidget(w)
    w.home.btn_image.click()
    assert w.stack.currentWidget() is w.image_screen


def test_le_moteur_ocr_est_branche_mais_pas_encore_charge(qtbot):
    """Le fournisseur est installé, mais rien de lourd n'est construit au
    démarrage : l'application doit s'ouvrir instantanément."""
    w = MainWindow()
    qtbot.addWidget(w)
    assert callable(w.image_screen.ocr_provider)
    assert w.image_screen.ocr_provider is not NullOcr


def test_le_referentiel_est_propage_a_l_ecran_image(qtbot):
    """Un changement de règles ou de types doit atteindre l'écran image comme
    les autres, sinon il détecte selon un référentiel périmé."""
    w = MainWindow()
    qtbot.addWidget(w)
    sentinelle = object()
    w.ref = sentinelle
    w._apply_prefs()
    assert w.image_screen.ref is w.ref


def test_la_banniere_de_mode_degrade_est_masquee_quand_le_modele_arrive(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)
    w._on_model_ready()
    assert not w.image_screen.banner.isVisibleTo(w.image_screen)
