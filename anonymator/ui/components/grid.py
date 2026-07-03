from PySide6.QtGui import QPainter, QPen, QColor
from anonymator.ui.theme import color

# Fond quadrillé identique au panneau gauche de l'accueil (HeroPanel).
# Les couleurs sont désormais lues dans le thème actif (cf. theme.py).
GRID_STEP = 26


def grid_colors() -> tuple[str, str]:
    """(fond, ligne) du quadrillage pour le thème actif."""
    return color("grid_bg"), color("grid_line")


def paint_grid(widget, bg: str | None = None, line: str | None = None,
               step: int = GRID_STEP) -> None:
    """Peint un fond + une grille de cadrage légère sur *widget*.

    Sans argument, lit le thème actif (`grid_bg`/`grid_line`). À appeler depuis
    le paintEvent d'un QWidget dont l'objectName porte le même fond en QSS."""
    if bg is None:
        bg = color("grid_bg")
    if line is None:
        line = color("grid_line")
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
