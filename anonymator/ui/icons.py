from pathlib import Path
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtCore import Qt
from PySide6.QtSvg import QSvgRenderer

_DIR = Path(__file__).parent / "assets" / "icons"
ICON_NAMES = ["document", "folder", "settings", "chevron-right",
              "shield", "layers", "eye-off", "alert",
              "sparkle", "scan", "home",
              "person", "user", "building", "map-pin", "mail", "phone",
              "credit-card", "scale", "id-card", "globe", "lock", "eye",
              "trash", "palette", "cpu", "github", "package"]


def icon(name: str, color: str | None = None, size: int = 24) -> QIcon:
    path = _DIR / f"{name}.svg"
    renderer = QSvgRenderer(str(path))
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    renderer.render(painter)
    if color is not None:
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(pix.rect(), QColor(color))
    painter.end()
    return QIcon(pix)
