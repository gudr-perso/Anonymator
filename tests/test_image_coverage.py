from anonymator.files import coverage
from anonymator.files.image import COVERAGE_IMAGE


def test_le_registre_expose_les_formats_documentaires_et_l_image():
    assert set(coverage.COVERAGE_BY_FORMAT) >= {"docx", "pptx", "xlsx", "image"}


def test_le_perimetre_image_annonce_ses_limites():
    non = " ".join(COVERAGE_IMAGE["non_traite"]).lower()
    assert "manuscrit" in non
    assert "visage" in non


def test_le_perimetre_image_ne_promet_pas_l_exhaustivite():
    traite = " ".join(COVERAGE_IMAGE["traite"]).lower()
    assert "propos" in traite        # « proposé à votre validation »
    assert "analysé" not in traite


def test_la_carte_perimetre_accepte_le_format_image():
    from anonymator.ui.components.perimetre_card import PerimetreCard
    card = PerimetreCard("image")
    assert "manuscrit" in card.rendered_text().lower()
