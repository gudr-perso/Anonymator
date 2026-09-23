import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_license_file_present_and_is_agpl():
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "GNU AFFERO GENERAL PUBLIC LICENSE" in text
    assert "Version 3" in text
    assert len(text) > 30_000


def test_pyproject_declares_agpl_spdx():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["license"] == "AGPL-3.0-or-later"


def test_spec_bundles_license_in_zip():
    spec = (ROOT / "anonymator.spec").read_text(encoding="utf-8")
    assert "'LICENSE'" in spec


def test_example_dataset_is_present_in_repo():
    """Le jeu de démonstration existe et porte des données fictives."""
    exdir = ROOT / "exemples"
    assert (exdir / "clients_demo.csv").exists()
    assert (exdir / "clients_demo.xlsx").exists()
    assert (exdir / "compte_rendu_reunion_demo.pdf").exists()
    assert (exdir / "Contrat_prestation_Ateliers_Tanguy_EURL.docx").exists()
    assert (exdir / "Bulletin_de_paie_2025-06_LACROIX_Damien.pdf").exists()
    # Nom normalisé <Siren>FEC<AAAAMMJJ de clôture>.txt (art. A. 47 A-1 du LPF)
    assert (exdir / "404833048FEC20251231.txt").exists()
    # Fiche de lecture du jeu : ce que contient chaque fichier, quoi vérifier.
    assert (exdir / "README.md").exists()


def test_build_script_ships_examples_next_to_exe():
    """Le build copie le dossier d'exemples à la racine du dossier distribué,
    pour que l'utilisateur les trouve à côté de l'exe (comme le LICENSE)."""
    script = (ROOT / "scripts" / "build.ps1").read_text(encoding="utf-8")
    assert "exemples" in script
