from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QComboBox, QLineEdit, QFileDialog)


class SettingsScreen(QWidget):
    def __init__(self, ref, prefs, on_apply, on_back):
        super().__init__()
        self.ref, self.prefs, self.on_apply = ref, prefs, on_apply
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Paramètres"))
        layout.addWidget(QLabel("Thème"))
        self.theme_box = QComboBox()
        self.theme_box.addItems(["cuma", "cap"])
        self.theme_box.setCurrentText(prefs.theme)
        self.theme_box.currentTextChanged.connect(self.select_theme)
        layout.addWidget(self.theme_box)
        layout.addWidget(QLabel("Dossier de sortie"))
        row = QHBoxLayout()
        self.dir_edit = QLineEdit(prefs.output_dir or "")
        btn_dir = QPushButton("Choisir…")
        btn_dir.clicked.connect(self._choose_dir)
        row.addWidget(self.dir_edit)
        row.addWidget(btn_dir)
        layout.addLayout(row)
        back = QPushButton("Accueil")
        back.setObjectName("ghost")
        back.clicked.connect(on_back)
        layout.addStretch()
        layout.addWidget(back)

    def select_theme(self, theme: str):
        self.prefs.theme = theme
        self.on_apply()

    def _choose_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Dossier de sortie")
        if path:
            self.dir_edit.setText(path)
            self.prefs.output_dir = path
            self.on_apply()
