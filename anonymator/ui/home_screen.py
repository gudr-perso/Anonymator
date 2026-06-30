from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt


class HomeScreen(QWidget):
    def __init__(self, on_text, on_file, on_settings):
        super().__init__()
        layout = QVBoxLayout(self)
        title = QLabel("Anonymator")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)
        self.btn_text = QPushButton("Texte")
        self.btn_file = QPushButton("Fichier")
        self.btn_settings = QPushButton("Paramètres")
        self.btn_settings.setObjectName("ghost")
        self.btn_text.clicked.connect(on_text)
        self.btn_file.clicked.connect(on_file)
        self.btn_settings.clicked.connect(on_settings)
        for w in (title, self.btn_text, self.btn_file, self.btn_settings):
            layout.addWidget(w)
        layout.addStretch()
