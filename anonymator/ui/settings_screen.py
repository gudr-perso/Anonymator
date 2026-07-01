from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QComboBox, QLineEdit, QFileDialog,
                               QListWidget, QListWidgetItem, QScrollArea, QProgressBar)
from anonymator.ui.components.header import HeaderBand
from anonymator.ui.components.toggle import ToggleSwitch
from anonymator.referential import Referential
from anonymator.core.model_status import is_model_available, installed_size
from anonymator.ui.download_worker import DownloadWorker
from anonymator.ui.about import about_lines

_TYPES = ["PERSON", "ADDRESS", "ORG", "EMAIL", "PHONE", "IBAN", "BIC",
          "SIREN", "SIRET", "NIR", "POSTAL_CODE", "URL", "LOGIN", "PASSWORD"]


class SettingsScreen(QWidget):
    model_ready = Signal()

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

        self._dl_worker: DownloadWorker | None = None
        root.addWidget(QLabel("Modèle de détection (noms, adresses, organisations)"))
        explain = QLabel(
            "La détection intelligente des noms, adresses et organisations utilise "
            "le modèle GLiNER (~300 Mo), téléchargé une seule fois puis utilisé hors ligne. "
            "Sans lui, les détections par règles (IBAN, e-mail, téléphone, mots de passe…) "
            "fonctionnent quand même.")
        explain.setWordWrap(True); explain.setObjectName("muted")
        root.addWidget(explain)
        self.model_status_label = QLabel("")
        root.addWidget(self.model_status_label)
        self.model_location_label = QLabel(""); self.model_location_label.setObjectName("muted")
        self.model_location_label.setWordWrap(True)
        root.addWidget(self.model_location_label)
        self.btn_model = QPushButton(""); self.btn_model.setObjectName("primary")
        self.btn_model.clicked.connect(self.start_model_download)
        root.addWidget(self.btn_model)
        self.model_progress = QProgressBar(); self.model_progress.setVisible(False)
        root.addWidget(self.model_progress)
        self.model_dl_status = QLabel(""); self.model_dl_status.setObjectName("muted")
        root.addWidget(self.model_dl_status)
        self._refresh_model_section()
        root.addWidget(QLabel("À propos"))
        self.about_label = QLabel("\n".join(about_lines()))
        self.about_label.setObjectName("muted")
        self.about_label.setWordWrap(True)
        root.addWidget(self.about_label)

    @staticmethod
    def _human_mb(n: int) -> str:
        return f"{n / (1024 * 1024):.0f} Mo"

    def _refresh_model_section(self):
        from anonymator.core.model_status import model_cache_dir
        if is_model_available():
            size = installed_size() or 0
            self.model_status_label.setText(f"✅ Installé ({self._human_mb(size)})")
            self.btn_model.setText("Réparer (re-télécharger)")
        else:
            self.model_status_label.setText("⬜ Non installé")
            self.btn_model.setText("Télécharger")
        self.model_location_label.setText(f"Emplacement : {model_cache_dir()}")

    def start_model_download(self):
        if self._dl_worker is not None and self._dl_worker.isRunning():
            return
        self.btn_model.setEnabled(False)
        self.model_progress.setVisible(True)
        self.model_progress.setRange(0, 0)
        self.model_dl_status.setText("Démarrage…")
        self._dl_worker = DownloadWorker()
        self._dl_worker.progress.connect(self._on_model_progress)
        self._dl_worker.status.connect(self.model_dl_status.setText)
        self._dl_worker.download_finished.connect(self._on_model_finished)
        self._dl_worker.error.connect(self._on_model_error)
        self._dl_worker.finished.connect(self._dl_worker.deleteLater)
        self._dl_worker.start()

    def _on_model_progress(self, received: int, total: int):
        if total > 0:
            self.model_progress.setRange(0, total)
            self.model_progress.setValue(received)
            self.model_dl_status.setText(
                f"{self._human_mb(received)} / {self._human_mb(total)} "
                f"— {received * 100 // total} %")
        else:
            self.model_progress.setRange(0, 0)

    def _on_model_finished(self):
        self.model_progress.setVisible(False)
        self.btn_model.setEnabled(True)
        self._refresh_model_section()
        self.model_dl_status.setText("Modèle prêt.")
        self.model_ready.emit()

    def _on_model_error(self, msg: str):
        self.model_progress.setVisible(False)
        self.btn_model.setEnabled(True)
        self.model_dl_status.setText(f"Erreur : {msg}")

    def stop_download(self):
        """Arrête proprement le worker de téléchargement s'il tourne encore.
        Appelable depuis MainWindow (ce widget est un enfant du QStackedWidget,
        donc son closeEvent ne se déclenche pas à la fermeture de la fenêtre)."""
        if self._dl_worker is not None and self._dl_worker.isRunning():
            self._dl_worker.quit(); self._dl_worker.wait()

    def closeEvent(self, event):
        self.stop_download()
        super().closeEvent(event)

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
