# anonymator/files/pdf/mapping.py
"""Compatibilité : le mapping vit désormais dans anonymator.files.textlayer,
qui ne dépend d'aucun format. Ce module reste le point d'entrée historique."""
from anonymator.files.textlayer import (  # noqa: F401
    Rect, rects_for_entity, rects_for_entities)
