from PySide6.QtWidgets import QAbstractButton
from PySide6.QtGui import QPainter, QColor
from PySide6.QtCore import Qt, QSize

_ON = "#00965E"
_OFF = "#C7D2CC"


class ToggleSwitch(QAbstractButton):
    """Interrupteur on/off stylé (vert)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(44, 24)

    def sizeHint(self) -> QSize:
        return QSize(44, 24)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        track = QColor(_ON if self.isChecked() else _OFF)
        p.setBrush(track)
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(self.rect(), 12, 12)
        d = 18
        x = self.width() - d - 3 if self.isChecked() else 3
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(x, 3, d, d)
        p.end()
