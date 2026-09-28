# anonymator/files/coverage.py
"""Registre des périmètres par format.

Chaque famille de formats définit son propre périmètre au plus près de son
code ; ce module les rassemble pour l'UI, qui n'a pas à savoir d'où ils
viennent."""
from anonymator.files import ooxml
from anonymator.files.image import COVERAGE_IMAGE

COVERAGE_BY_FORMAT = {
    **ooxml.COVERAGE_BY_FORMAT,
    "image": COVERAGE_IMAGE,
}
