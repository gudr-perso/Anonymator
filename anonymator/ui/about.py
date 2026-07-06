"""Mentions légales « À propos » — conformité AGPL-3.0.

Fonction pure : produit les lignes affichées par l'UI à partir de la version.
Aucun accès git ni réseau (compatible exe PyInstaller gelé). La mention du tag
exact satisfait la correspondance « source = binaire » exigée par l'AGPL art. 6.
"""

from anonymator import __version__
from anonymator.brand import active_brand

REPO_URL = "https://github.com/gudr-perso/Anonymator"


def about_lines(version: str = __version__) -> list[str]:
    return [
        f"{active_brand().product_name} v{version}",
        f"Licence : AGPL-3.0 — code source : {REPO_URL} (tag v{version})",
        "Embarque PyMuPDF © Artifex Software — AGPL-3.0",
        "Embarque GLiNER (urchade/gliner_multi-v2.1) — Apache-2.0",
    ]
