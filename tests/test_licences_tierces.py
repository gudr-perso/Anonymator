from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
DOSSIER = RACINE / "third-party-licenses"


def test_le_texte_apache_est_fourni():
    texte = (DOSSIER / "Apache-2.0.txt").read_text(encoding="utf-8")
    assert "Apache License" in texte
    assert "Version 2.0" in texte


def test_le_tableau_cite_rapidocr():
    readme = (DOSSIER / "README.md").read_text(encoding="utf-8")
    assert "rapidocr" in readme.lower()


def test_la_redistribution_des_modeles_ocr_est_annoncee():
    """Les poids GLiNER sont téléchargés, donc non redistribués ; les modèles
    PP-OCR, eux, partent dans l'exécutable. L'obligation d'attribution n'est
    pas la même — le dossier doit le dire."""
    readme = (DOSSIER / "README.md").read_text(encoding="utf-8")
    assert "PP-OCR" in readme
    assert "redistribu" in readme.lower()


def test_requirements_impose_la_variante_headless_d_opencv():
    """opencv-python (variante complète) embarque ses propres plugins Qt et
    entre en conflit avec PySide6 sous PyInstaller."""
    req = (RACINE / "requirements.txt").read_text(encoding="utf-8")
    assert "opencv-python-headless" in req
    lignes_opencv = [l for l in req.splitlines()
                     if l.strip().startswith("opencv")]
    assert lignes_opencv == ["opencv-python-headless>=4.10"]
