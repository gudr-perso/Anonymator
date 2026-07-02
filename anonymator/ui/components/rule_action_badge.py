from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


class RuleActionBadge(QLabel):
    """Badge coloré pour l'action d'une règle. action ∈ {'keep','mask'}."""
    _KEEP = "#00965E"
    _MASK = "#E8621A"

    def __init__(self, action: str, parent=None):
        keep = action == "keep"
        text = "👁  Ne jamais masquer" if keep else "🚫  Toujours masquer"
        color = self._KEEP if keep else self._MASK
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(
            f"background: {_rgba(color, 0.14)}; color: {color}; border-radius: 8px;"
            f"padding: 3px 10px; font-size: 12px; font-weight: 700;")
