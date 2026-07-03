from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt
from anonymator.ui.icons import icon
from anonymator.ui.theme import color


class NavBand(QFrame):
    """Bandeau d'onglets : « Accueil » + onglet de l'écran actif (souligné).

    home_btn : retour accueil. active_btn : onglet non cliquable de l'écran courant.
    Sur l'écran Accueil, passer title="Accueil"/icon="home" et on_home=None."""
    def __init__(self, title: str, icon_name: str, on_home=None, parent=None):
        super().__init__(parent)
        self.setObjectName("NavBand")
        row = QHBoxLayout(self)
        row.setContentsMargins(16, 0, 16, 0)
        row.setSpacing(4)

        self.home_btn = QPushButton("  Accueil")
        self.home_btn.setObjectName("tab")
        self.home_btn.setIcon(icon("home", color("text_muted"), 18))
        self.home_btn.setCursor(Qt.PointingHandCursor)
        if on_home is not None:
            self.home_btn.clicked.connect(on_home)
        else:
            self.home_btn.setObjectName("tabActive")

        self.active_btn = QPushButton("  " + title)
        self.active_btn.setObjectName("tabActive")
        self.active_btn.setIcon(icon(icon_name, color("action"), 18))
        self.active_btn.setEnabled(False)

        row.addWidget(self.home_btn)
        if on_home is not None:
            row.addWidget(self.active_btn)
        row.addStretch()
