from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_readme_has_licence_section():
    txt = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "## Licence" in txt
    assert "AGPL-3.0" in txt
    assert "https://github.com/gudr-perso/Anonymator" in txt
    # Attribution PyMuPDF requise par la conformité.
    assert "PyMuPDF" in txt and "Artifex" in txt
    # Lien vers le fichier LICENSE.
    assert "LICENSE" in txt
