from PySide6.QtWidgets import QAbstractButton
from PySide6.QtGui import QPainter, QColor
from PySide6.QtCore import Qt, QSize

from anonymator.ui.theme import color


class ToggleSwitch(QAbstractButton):
    """Interrupteur on/off stylé (vert)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(44, 24)

    def sizeHint(self) -> QSize:
        return QSize(44, 24)

    def track_color(self) -> str:
        return color("action") if self.isChecked() else color("toggle_off")

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor(self.track_color()))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(self.rect(), 12, 12)
        d = 18
        x = self.width() - d - 3 if self.isChecked() else 3
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(x, 3, d, d)
        p.end()
