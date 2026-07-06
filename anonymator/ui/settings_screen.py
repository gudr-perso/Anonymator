from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                               QPushButton, QLabel, QComboBox, QLineEdit,
                               QFileDialog, QScrollArea, QProgressBar)
from anonymator.ui.components.header import HeaderBand
from anonymator.ui.components.nav_band import NavBand
from anonymator.ui.components.cards import Card
from anonymator.ui.components.entity_card import EntityCard
from anonymator.ui.theme import THEME_LABELS, label_for_theme, theme_for_label
from anonymator.brand import is_locked
from anonymator.referential import Referential
from anonymator.core.model_status import is_model_available, installed_size
from anonymator.ui.download_worker import DownloadWorker

_TYPES = ["PERSON", "ADDRESS", "ORG", "EMAIL", "PHONE", "IBAN", "BIC",
          "SIREN", "SIRET", "NIR", "POSTAL_CODE", "URL", "LOGIN", "PASSWORD"]


class SettingsScreen(QWidget):
    model_ready = Signal()

    def __init__(self, ref, prefs, on_apply, on_back):
        super().__init__()
        self.ref, self.prefs, self.on_apply = ref, prefs, on_apply

        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)
        root.addWidget(HeaderBand())
        root.addWidget(NavBand("Détection & masquage", "settings", on_home=on_back))

        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QScrollArea.NoFrame)
        host = QWidget(); body = QVBoxLayout(host)
        body.setContentsMargins(40, 24, 40, 40); body.setSpacing(18)
        scroll.setWidget(host); root.addWidget(scroll)

        title = QLabel("Détection & masquage"); title.setObjectName("title")
        subtitle = QLabel("Réglez le thème, la sortie et ce que l'application repère automatiquement.")
        subtitle.setObjectName("muted")
        body.addWidget(title); body.addWidget(subtitle)

        # --- Carte GÉNÉRAL ---
        general = Card("palette", "Général")
        if not is_locked():
            general.body.addWidget(QLabel("Thème de l'application"))
            self.theme_box = QComboBox()
            self.theme_box.addItems([THEME_LABELS[k] for k in ("cuma", "cap")])
            self.theme_box.setCurrentText(label_for_theme(prefs.theme))
            self.theme_box.currentTextChanged.connect(
                lambda lbl: self.select_theme(theme_for_label(lbl)))
            general.body.addWidget(self.theme_box)
        general.body.addWidget(QLabel("Dossier de sortie"))
        row = QHBoxLayout()
        self.dir_edit = QLineEdit(prefs.output_dir or "")
        btn_dir = QPushButton("Choisir…"); btn_dir.setObjectName("secondary")
        btn_dir.clicked.connect(self._choose_dir)
        row.addWidget(self.dir_edit); row.addWidget(btn_dir)
        general.body.addLayout(row)
        body.addWidget(general)

        # --- Carte TYPES D'ENTITÉS ---
        types_card = Card("shield", "Types d'entités à détecter")
        self.count_badge = QLabel(""); self.count_badge.setObjectName("occBadge")
        types_card.head.addWidget(self.count_badge)
        grid = QGridLayout(); grid.setSpacing(10)
        self._type_toggles = {}
        for i, code in enumerate(_TYPES):
            card = EntityCard(code, active=self.ref.is_active(code))
            card.toggled.connect(self.set_type_active)
            grid.addWidget(card, i // 2, i % 2)
            self._type_toggles[code] = card.toggle
        types_card.body.addLayout(grid)
        body.addWidget(types_card)
        self._refresh_type_count()

        # --- Carte MODÈLE ---
        self._dl_worker = None
        model_card = Card("cpu", "Modèle de détection intelligente")
        explain = QLabel(
            "La détection intelligente des noms, adresses et organisations utilise "
            "le modèle GLiNER (~300 Mo), téléchargé une seule fois puis utilisé hors ligne. "
            "Sans lui, les détections par règles (IBAN, e-mail, téléphone, mots de passe…) "
            "fonctionnent quand même.")
        explain.setWordWrap(True); explain.setObjectName("muted")
        model_card.body.addWidget(explain)
        self.model_status_label = QLabel(""); model_card.body.addWidget(self.model_status_label)
        self.model_location_label = QLabel(""); self.model_location_label.setObjectName("muted")
        self.model_location_label.setWordWrap(True); model_card.body.addWidget(self.model_location_label)
        self.btn_model = QPushButton(""); self.btn_model.setObjectName("primary")
        self.btn_model.clicked.connect(self.start_model_download); model_card.body.addWidget(self.btn_model)
        self.model_progress = QProgressBar(); self.model_progress.setVisible(False)
        model_card.body.addWidget(self.model_progress)
        self.model_dl_status = QLabel(""); self.model_dl_status.setObjectName("muted")
        model_card.body.addWidget(self.model_dl_status)
        body.addWidget(model_card)
        body.addStretch()
        self._refresh_model_section()

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

    def _refresh_type_count(self):
        n = sum(1 for t in self._type_toggles.values() if t.isChecked())
        self.count_badge.setText(f"{n} / {len(_TYPES)} actifs")

    def set_type_active(self, code: str, active: bool):
        self.prefs.entity_overrides[code] = active
        self._refresh_type_count()
        self.on_apply()

    def _choose_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Dossier de sortie")
        if path:
            self.dir_edit.setText(path); self.prefs.output_dir = path; self.on_apply()
