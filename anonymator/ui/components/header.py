from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel
from anonymator.ui.icons import icon


class HeaderBand(QFrame):
    """Bandeau d'en-tête : logo + nom de l'app + réseau."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("HeaderBand")
        row = QHBoxLayout(self)
        logo = QLabel(); logo.setPixmap(icon("shield", "#31B700").pixmap(20, 20))
        name = QLabel("Anonymator"); name.setStyleSheet("font-weight: 700;")
        sep = QLabel("|"); sep.setObjectName("muted")
        net = QLabel("RÉSEAU CUMA"); net.setObjectName("muted")
        net.setStyleSheet("font-weight: 700; letter-spacing: 1px;")
        for w in (logo, name, sep, net):
            row.addWidget(w)
        row.addStretch()
