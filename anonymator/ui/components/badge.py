from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt
from anonymator.ui.colors import color_for


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


class CategoryBadge(QLabel):
    """Étiquette arrondie colorée pour une typologie.

    Fond teinté léger (rgba — Qt QSS ne gère pas le hex à 8 chiffres) + texte de
    la couleur du type, cohérent avec le surlignage du texte."""
    def __init__(self, etype: str, label: str | None = None, parent=None):
        super().__init__(label or etype, parent)
        c = color_for(etype)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(
            f"background: {_rgba(c, 0.16)}; color: {c}; border-radius: 8px;"
            f"padding: 2px 9px; font-size: 11px; font-weight: 700;")
