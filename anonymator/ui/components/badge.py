from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt
from anonymator.ui.colors import color_for


class CategoryBadge(QLabel):
    """Étiquette arrondie colorée pour une typologie."""
    def __init__(self, etype: str, label: str | None = None, parent=None):
        super().__init__(label or etype, parent)
        c = color_for(etype)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(
            f"background: {c}22; color: {c}; border-radius: 8px;"
            f"padding: 2px 8px; font-size: 11px; font-weight: 700;")
