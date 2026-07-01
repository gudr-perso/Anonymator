import anonymator
from anonymator.ui.about import REPO_URL, about_lines


def test_about_lines_mention_version_and_tag():
    v = anonymator.__version__
    joined = "\n".join(about_lines())
    assert f"Anonymator v{v}" in joined
    assert f"tag v{v}" in joined


def test_about_lines_mention_licence_and_source():
    joined = "\n".join(about_lines())
    assert "AGPL-3.0" in joined
    assert REPO_URL in joined


def test_about_lines_attribute_pymupdf_and_gliner():
    joined = "\n".join(about_lines())
    assert "PyMuPDF" in joined and "Artifex" in joined
    assert "GLiNER" in joined and "Apache-2.0" in joined


def test_about_lines_accepts_explicit_version():
    lines = about_lines(version="9.9.9")
    joined = "\n".join(lines)
    assert "Anonymator v9.9.9" in joined
    assert "tag v9.9.9" in joined
