from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QComboBox, QLineEdit, QFileDialog,
                               QListWidget, QListWidgetItem, QScrollArea)
from anonymator.ui.components.header import HeaderBand
from anonymator.ui.components.toggle import ToggleSwitch
from anonymator.referential import Referential

_TYPES = ["PERSON", "ADDRESS", "ORG", "EMAIL", "PHONE", "IBAN", "BIC",
          "SIREN", "SIRET", "NIR", "POSTAL_CODE", "URL", "LOGIN", "PASSWORD"]


class SettingsScreen(QWidget):
    def __init__(self, ref, prefs, on_apply, on_back):
        super().__init__()
        self.ref, self.prefs, self.on_apply = ref, prefs, on_apply
        root = QVBoxLayout(self)
        root.addWidget(HeaderBand())
        nav = QHBoxLayout()
        back = QPushButton("Accueil"); back.setObjectName("ghost"); back.clicked.connect(on_back)
        nav.addWidget(back); nav.addWidget(QLabel("Règles de détection & masquage")); nav.addStretch()
        root.addLayout(nav)

        root.addWidget(QLabel("Thème"))
        self.theme_box = QComboBox(); self.theme_box.addItems(["cuma", "cap"])
        self.theme_box.setCurrentText(prefs.theme)
        self.theme_box.currentTextChanged.connect(self.select_theme)
        root.addWidget(self.theme_box)

        root.addWidget(QLabel("Dossier de sortie"))
        row = QHBoxLayout()
        self.dir_edit = QLineEdit(prefs.output_dir or "")
        btn_dir = QPushButton("Choisir…"); btn_dir.setObjectName("secondary"); btn_dir.clicked.connect(self._choose_dir)
        row.addWidget(self.dir_edit); row.addWidget(btn_dir)
        root.addLayout(row)

        root.addWidget(QLabel("Types d'entités à détecter"))
        self._type_toggles = {}
        grid = QScrollArea(); grid.setWidgetResizable(True)
        host = QWidget(); hv = QVBoxLayout(host)
        for code in _TYPES:
            r = QHBoxLayout(); lbl = QLabel(code); tog = ToggleSwitch()
            tog.setChecked(self.ref.is_active(code))
            tog.toggled.connect(lambda on, c=code: self.set_type_active(c, on))
            r.addWidget(lbl); r.addStretch(); r.addWidget(tog)
            hv.addLayout(r); self._type_toggles[code] = tog
        grid.setWidget(host); root.addWidget(grid)

        root.addWidget(QLabel("Liste d'exclusion (NER)"))
        base = self.prefs.ner_stoplist
        if base is None:
            base = sorted(Referential.load_default().ner_stoplist())
        self.prefs.ner_stoplist = list(base)
        add_row = QHBoxLayout()
        self.stop_edit = QLineEdit()
        add = QPushButton("Ajouter"); add.setObjectName("secondary")
        add.clicked.connect(lambda: self.add_stop_term(self.stop_edit.text().strip()))
        add_row.addWidget(self.stop_edit); add_row.addWidget(add)
        root.addLayout(add_row)
        self.stop_list = QListWidget(); root.addWidget(self.stop_list)
        self._reload_stoplist()

    def select_theme(self, theme: str):
        self.prefs.theme = theme
        self.on_apply()

    def set_type_active(self, code: str, active: bool):
        self.prefs.entity_overrides[code] = active
        self.on_apply()

    def _reload_stoplist(self):
        self.stop_list.clear()
        for term in self.prefs.ner_stoplist:
            host = QWidget(); h = QHBoxLayout(host); h.setContentsMargins(0, 0, 0, 0)
            h.addWidget(QLabel(term)); h.addStretch()
            x = QPushButton("✕"); x.setObjectName("ghost"); x.setFixedWidth(30)
            x.clicked.connect(lambda _=False, t=term: self.remove_stop_term(t))
            h.addWidget(x)
            it = QListWidgetItem(); it.setSizeHint(host.sizeHint())
            self.stop_list.addItem(it); self.stop_list.setItemWidget(it, host)

    def add_stop_term(self, term: str):
        if term and term not in self.prefs.ner_stoplist:
            self.prefs.ner_stoplist.append(term)
            self.stop_edit.clear(); self._reload_stoplist(); self.on_apply()

    def remove_stop_term(self, term: str):
        if term in self.prefs.ner_stoplist:
            self.prefs.ner_stoplist.remove(term)
            self._reload_stoplist(); self.on_apply()

    def _choose_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Dossier de sortie")
        if path:
            self.dir_edit.setText(path); self.prefs.output_dir = path; self.on_apply()
