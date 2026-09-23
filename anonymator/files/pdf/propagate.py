# anonymator/files/pdf/propagate.py
"""Compatibilité : la propagation vit désormais dans anonymator.files.textlayer.
Elle ne dépend d'aucun format — seulement de WordBox et d'Entity."""
from anonymator.files.textlayer import propagate_across_pages  # noqa: F401
