# anonymator/ui/pdf_canvas.py
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsRectItem
from PySide6.QtGui import QImage, QPixmap, QColor, QPen, QBrush
from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from anonymator.ui.colors import color_for

Rect = tuple[float, float, float, float]


def scene_rect_to_points(x0: float, y0: float, x1: float, y1: float,
                         zoom: float) -> Rect:
    """Convertit un rectangle en coordonnées scène (pixels) vers des points PDF,
    en normalisant l'ordre des coins."""
    return (min(x0, x1) / zoom, min(y0, y1) / zoom,
            max(x0, x1) / zoom, max(y0, y1) / zoom)


class PdfCanvas(QGraphicsView):
    """Affiche une page rendue + overlays de rectangles. En mode tracé, un
    glisser produit un rectangle manuel (émis en points PDF)."""

    manual_rect_drawn = Signal(tuple)   # (x0, y0, x1, y1) en points PDF

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHints(self.renderHints())
        self._zoom = 2.0
        self._pixmap_item = None
        self._overlay_items: list[QGraphicsRectItem] = []
        self._draw_mode = False
        self._origin: QPointF | None = None
        self._rubber: QGraphicsRectItem | None = None

    def has_page(self) -> bool:
        return self._pixmap_item is not None

    def overlay_count(self) -> int:
        return len(self._overlay_items)

    def set_draw_mode(self, on: bool) -> None:
        self._draw_mode = on
        self.setCursor(Qt.CrossCursor if on else Qt.ArrowCursor)

    def set_page(self, png: bytes, zoom: float) -> None:
        self._zoom = zoom
        self._scene.clear()
        self._overlay_items = []
        self._rubber = None
        img = QImage.fromData(png, "PNG")
        self._pixmap_item = self._scene.addPixmap(QPixmap.fromImage(img))
        self._scene.setSceneRect(self._pixmap_item.boundingRect())

    def set_overlays(self, entity_rects: list[tuple[Rect, str]],
                     manual_rects: list[Rect]) -> None:
        for item in self._overlay_items:
            self._scene.removeItem(item)
        self._overlay_items = []
        for rect, etype in entity_rects:
            self._add_overlay(rect, QColor(color_for(etype)), dashed=False)
        for rect in manual_rects:
            self._add_overlay(rect, QColor("#20202A"), dashed=True)

    def _add_overlay(self, rect: Rect, color: QColor, dashed: bool) -> None:
        x0, y0, x1, y1 = (v * self._zoom for v in rect)
        item = QGraphicsRectItem(QRectF(x0, y0, x1 - x0, y1 - y0))
        pen = QPen(color); pen.setWidth(2)
        if dashed:
            pen.setStyle(Qt.DashLine)
        item.setPen(pen)
        fill = QColor(color); fill.setAlpha(70)
        item.setBrush(QBrush(fill))
        self._scene.addItem(item)
        self._overlay_items.append(item)

    # --- tracé manuel ---
    def mousePressEvent(self, event):
        if self._draw_mode and event.button() == Qt.LeftButton and self.has_page():
            self._origin = self.mapToScene(event.position().toPoint())
            self._rubber = QGraphicsRectItem()
            pen = QPen(QColor("#20202A")); pen.setStyle(Qt.DashLine); pen.setWidth(2)
            self._rubber.setPen(pen)
            self._scene.addItem(self._rubber)
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._rubber is not None and self._origin is not None:
            cur = self.mapToScene(event.position().toPoint())
            self._rubber.setRect(QRectF(self._origin, cur).normalized())
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._rubber is not None and self._origin is not None:
            cur = self.mapToScene(event.position().toPoint())
            self._scene.removeItem(self._rubber)
            self._rubber = None
            self._finish_manual((self._origin.x(), self._origin.y()),
                                (cur.x(), cur.y()))
            self._origin = None
            return
        super().mouseReleaseEvent(event)

    def _finish_manual(self, p0: tuple[float, float],
                       p1: tuple[float, float]) -> None:
        pts = scene_rect_to_points(p0[0], p0[1], p1[0], p1[1], self._zoom)
        # ignore les tracés dégénérés (clic sans glisser)
        if pts[2] - pts[0] < 1 or pts[3] - pts[1] < 1:
            return
        self.manual_rect_drawn.emit(pts)
