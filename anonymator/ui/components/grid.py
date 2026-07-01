from PySide6.QtGui import QPainter, QPen, QColor

# Fond quadrillé identique au panneau gauche de l'accueil (HeroPanel).
GRID_BG = "#E8F3EA"
GRID_LINE = "#E1EBE3"
GRID_STEP = 26


def paint_grid(widget, bg: str = GRID_BG, line: str = GRID_LINE,
               step: int = GRID_STEP) -> None:
    """Peint un fond vert pâle + une grille de cadrage légère sur *widget*.

    À appeler depuis le paintEvent d'un QWidget dont l'objectName porte le
    même fond en QSS (cf. #FileBg / #PdfBg)."""
    p = QPainter(widget)
    p.fillRect(widget.rect(), QColor(bg))
    pen = QPen(QColor(line)); pen.setWidth(1)
    p.setPen(pen)
    w, h = widget.width(), widget.height()
    x = step
    while x < w:
        p.drawLine(x, 0, x, h); x += step
    y = step
    while y < h:
        p.drawLine(0, y, w, y); y += step
    p.end()
