from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt
from anonymator.ui.icons import icon


class Card(QFrame):
    """Conteneur titré (icône + titre en capitales + corps via .body)."""
    def __init__(self, icon_name: str, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        outer = QVBoxLayout(self)
        self.head = QHBoxLayout()
        ic = QLabel(); ic.setPixmap(icon(icon_name, "#00965E").pixmap(16, 16))
        self.title_label = QLabel(title)
        self.title_label.setObjectName("sectionLabel")
        self.title_label.setStyleSheet("text-transform: uppercase;")
        self.head.addWidget(ic); self.head.addWidget(self.title_label); self.head.addStretch()
        outer.addLayout(self.head)
        self.body = QVBoxLayout()
        outer.addLayout(self.body)


class StatCard(QFrame):
    """Icône + grand nombre + libellé."""
    def __init__(self, icon_name: str, label: str, accent: str = "#00965E", parent=None):
        super().__init__(parent)
        self.setObjectName("StatCard")
        row = QHBoxLayout(self)
        ic = QLabel(); ic.setPixmap(icon(icon_name, accent).pixmap(20, 20))
        col = QVBoxLayout()
        self.value_label = QLabel("0")
        self.value_label.setStyleSheet("font-size: 22px; font-weight: 700;")
        lbl = QLabel(label); lbl.setObjectName("muted")
        col.addWidget(self.value_label); col.addWidget(lbl)
        row.addWidget(ic); row.addLayout(col); row.addStretch()

    def set_value(self, value) -> None:
        self.value_label.setText(str(value))


class NavCard(QFrame):
    """Carte cliquable : icône + titre + sous-titre + chevron."""
    def __init__(self, icon_name: str, title: str, subtitle: str,
                 on_click=None, parent=None):
        super().__init__(parent)
        self.setObjectName("NavCard")
        self.setCursor(Qt.PointingHandCursor)
        self._on_click = on_click
        row = QHBoxLayout(self)
        ic = QLabel(); ic.setPixmap(icon(icon_name, "#00965E").pixmap(22, 22))
        col = QVBoxLayout()
        t = QLabel(title); t.setStyleSheet("font-size: 15px; font-weight: 700;")
        s = QLabel(subtitle); s.setObjectName("muted")
        col.addWidget(t); col.addWidget(s)
        chev = QLabel(); chev.setPixmap(icon("chevron-right", "#6B7C72").pixmap(18, 18))
        row.addWidget(ic); row.addLayout(col); row.addStretch(); row.addWidget(chev)

    def _emit(self):
        if self._on_click:
            self._on_click()

    def click(self):
        """Déclenche l'action comme un clic (alias public de _emit, façon
        QAbstractButton.click) — pratique pour piloter la carte depuis les tests."""
        self._emit()

    def mouseReleaseEvent(self, event):
        self._emit()
        super().mouseReleaseEvent(event)
