from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton


class ModelBanner(QWidget):
    """Bandeau « mode dégradé » : noms/adresses/orgs non détectés faute de modèle."""
    def __init__(self, on_install=None, parent=None):
        super().__init__(parent)
        self.setObjectName("modelBanner")
        h = QHBoxLayout(self); h.setContentsMargins(12, 8, 12, 8); h.setSpacing(10)
        lbl = QLabel("⚠  Noms / adresses / organisations non détectés "
                     "(modèle non installé).")
        lbl.setWordWrap(True)
        self.btn = QPushButton("Installer maintenant"); self.btn.setObjectName("secondary")
        if on_install is not None:
            self.btn.clicked.connect(on_install)
        h.addWidget(lbl); h.addStretch(); h.addWidget(self.btn)
        self.setStyleSheet(
            "#modelBanner { background: rgba(232, 98, 26, 0.10); "
            "border: 1px solid rgba(232, 98, 26, 0.55); border-radius: 8px; }")
        self.hide()
