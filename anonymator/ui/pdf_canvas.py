# anonymator/ui/pdf_canvas.py
"""Compatibilité : le canevas est générique (page PDF rendue ou image) et vit
dans anonymator.ui.spatial_canvas."""
from anonymator.ui.spatial_canvas import (  # noqa: F401
    SpatialCanvas, scene_rect_to_source, Rect)

PdfCanvas = SpatialCanvas
scene_rect_to_points = scene_rect_to_source
