from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from anonymator.ui.components.header import HeaderBand
from anonymator.ui.about import about_lines


class AboutScreen(QWidget):
    def __init__(self, on_back):
        super().__init__()
        root = QVBoxLayout(self)
        root.addWidget(HeaderBand())
        nav = QHBoxLayout()
        self.back_btn = QPushButton("Accueil"); self.back_btn.setObjectName("ghost")
        self.back_btn.clicked.connect(on_back)
        nav.addWidget(self.back_btn); nav.addWidget(QLabel("À propos")); nav.addStretch()
        root.addLayout(nav)

        self.about_label = QLabel("\n".join(about_lines()))
        self.about_label.setObjectName("muted")
        self.about_label.setWordWrap(True)
        root.addWidget(self.about_label)
        root.addStretch()
