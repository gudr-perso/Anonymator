# anonymator/core/pdf_review_session.py
"""Compatibilité : la session de revue spatiale est générique (PDF ou image)
et vit dans anonymator.core.spatial_review_session."""
from anonymator.core.spatial_review_session import (  # noqa: F401
    SpatialReviewSession, Rect)

PdfReviewSession = SpatialReviewSession
