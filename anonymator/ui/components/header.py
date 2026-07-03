from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel
from anonymator.ui.icons import icon
from anonymator.ui.theme import color


class HeaderBand(QFrame):
    """Bandeau d'en-tête : logo + nom de l'app + étiquette réseau (thème)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("HeaderBand")
        row = QHBoxLayout(self)
        logo = QLabel(); logo.setPixmap(icon("shield", color("primary")).pixmap(20, 20))
        name = QLabel("Anonymator"); name.setStyleSheet("font-weight: 700;")
        row.addWidget(logo); row.addWidget(name)
        tag = color("header_tag")
        if tag:                                  # masqué (avec le séparateur) si vide
            sep = QLabel("|"); sep.setObjectName("muted")
            net = QLabel(tag); net.setObjectName("muted")
            net.setStyleSheet("font-weight: 700; letter-spacing: 1px;")
            row.addWidget(sep); row.addWidget(net)
        row.addStretch()
