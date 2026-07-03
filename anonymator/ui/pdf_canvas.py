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

    ZOOM_STEP = 1.25
    ZOOM_MIN = 0.25
    ZOOM_MAX = 8.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHints(self.renderHints())
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self._zoom = 2.0
        self._display = 1.0
        self._fit_width = False
        self._pixmap_item = None
        self._overlay_items: list[QGraphicsRectItem] = []
        self._draw_mode = False
        self._origin: QPointF | None = None
        self._rubber: QGraphicsRectItem | None = None

    def has_page(self) -> bool:
        return self._pixmap_item is not None

    def clear(self) -> None:
        """Vide le canevas (aucune page, aucun overlay) et remet le zoom à 1."""
        self._scene.clear()
        self._pixmap_item = None
        self._overlay_items = []
        self._rubber = None
        self.reset_zoom()

    def overlay_count(self) -> int:
        return len(self._overlay_items)

    def set_draw_mode(self, on: bool) -> None:
        self._draw_mode = on
        self.setCursor(Qt.CrossCursor if on else Qt.ArrowCursor)

    # --- zoom d'affichage (transformation de vue, indépendant de self._zoom
    #     qui reste le facteur de rasterisation scène ↔ points PDF) ---
    @property
    def display_zoom(self) -> float:
        return self._display

    def _apply_display_zoom(self) -> None:
        self.resetTransform()
        self.scale(self._display, self._display)

    def zoom_in(self) -> None:
        self._fit_width = False
        self._set_display_zoom(self._display * self.ZOOM_STEP)

    def zoom_out(self) -> None:
        self._fit_width = False
        self._set_display_zoom(self._display / self.ZOOM_STEP)

    def reset_zoom(self) -> None:
        self._fit_width = False
        self._set_display_zoom(1.0)

    def fit_to_width(self) -> None:
        """Ajuste le zoom pour que la largeur de la page remplisse la zone
        visible. Reste actif au redimensionnement jusqu'à un zoom manuel."""
        if not self.has_page():
            return
        self._fit_width = True
        self._apply_fit_width()

    def _apply_fit_width(self) -> None:
        avail = self.viewport().width() - 2   # petite marge
        scene_w = self._scene.width()
        if scene_w <= 0 or avail <= 0:
            return
        zoom = avail / scene_w
        # réserve la place de la barre de défilement verticale si la page déborde
        if self._scene.height() * zoom > self.viewport().height():
            avail -= self.verticalScrollBar().sizeHint().width()
            zoom = avail / scene_w
        self._set_display_zoom(zoom)

    def _set_display_zoom(self, value: float) -> None:
        self._display = max(self.ZOOM_MIN, min(self.ZOOM_MAX, value))
        self._apply_display_zoom()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._fit_width and self.has_page():
            self._apply_fit_width()

    def wheelEvent(self, event):
        # Ctrl + molette : zoome autour du curseur (AnchorUnderMouse).
        if event.modifiers() & Qt.ControlModifier and self.has_page():
            self.zoom_in() if event.angleDelta().y() > 0 else self.zoom_out()
            event.accept()
            return
        super().wheelEvent(event)

    def set_page(self, png: bytes, zoom: float) -> None:
        self._zoom = zoom
        self._scene.clear()
        self._overlay_items = []
        self._rubber = None
        img = QImage.fromData(png, "PNG")
        self._pixmap_item = self._scene.addPixmap(QPixmap.fromImage(img))
        self._scene.setSceneRect(self._pixmap_item.boundingRect())
        if self._fit_width:
            self._apply_fit_width()

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
