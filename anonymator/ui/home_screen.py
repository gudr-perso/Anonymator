from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel)
from PySide6.QtCore import Qt
from anonymator.ui.components.cards import NavCard


class HomeScreen(QWidget):
    def __init__(self, on_text, on_file, on_settings):
        super().__init__()
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        hero = QWidget(); hero.setObjectName("Hero")
        hero.setStyleSheet("#Hero { background: #E8F3EA; }")
        hv = QVBoxLayout(hero)
        hv.setContentsMargins(40, 40, 40, 40)
        logo = QLabel("CUMA"); logo.setObjectName("title")
        logo.setStyleSheet("color: #31B700; font-size: 34px; font-weight: 800;")
        title = QLabel("Anonymisez.\nPartagez l'essentiel.")
        title.setObjectName("title")
        sub = QLabel("Protégez noms, adresses et coordonnées avant tout partage. "
                     "Traitement 100% local, aucune donnée envoyée.")
        sub.setObjectName("muted"); sub.setWordWrap(True)
        hv.addWidget(logo); hv.addSpacing(120); hv.addWidget(title); hv.addWidget(sub)
        hv.addStretch()
        foot = QLabel("la puissance du <span style='color:#E8621A;font-weight:700'>groupe</span>")
        foot.setTextFormat(Qt.RichText)
        hv.addWidget(foot)

        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(40, 60, 40, 40)
        label = QLabel("PAR OÙ COMMENCER ?"); label.setObjectName("sectionLabel")
        rv.addWidget(label); rv.addSpacing(12)
        self.btn_text = NavCard("document", "Coller du texte",
                                "Analyser et masquer un texte collé", on_click=on_text)
        self.btn_file = NavCard("folder", "Importer un fichier",
                                ".txt, .csv ou .xlsx", on_click=on_file)
        self.btn_settings = NavCard("settings", "Paramètres",
                                    "Règles de détection & masquage", on_click=on_settings)
        for c in (self.btn_text, self.btn_file, self.btn_settings):
            rv.addWidget(c)
        rv.addStretch()

        root.addWidget(hero, 5)
        root.addWidget(right, 6)
