from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton,
                               QProgressBar, QTextEdit)
from PySide6.QtCore import Qt, Signal
from anonymator.ui.download_worker import DownloadWorker


class SetupScreen(QWidget):
    model_ready = Signal()

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        title = QLabel("Anonymator — Configuration initiale")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)
        desc = QLabel(
            "Le modèle de détection GLiNER (~300 Mo) doit être téléchargé\n"
            "une seule fois. Une connexion Internet est nécessaire."
        )
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        self.label_status = QLabel("Prêt.")
        self.label_status.setAlignment(Qt.AlignCenter)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)    # indéterminé
        self.progress.setVisible(False)
        self.btn_start = QPushButton("Télécharger le modèle")
        self.btn_start.clicked.connect(self._start)
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(100)
        for w in (title, desc, self.label_status, self.progress,
                  self.btn_start, self._log):
            layout.addWidget(w)
        layout.addStretch()
        self._worker: DownloadWorker | None = None

    def _start(self):
        self.btn_start.setEnabled(False)
        self.progress.setVisible(True)
        self.label_status.setText("Téléchargement en cours…")
        self._worker = DownloadWorker()
        self._worker.status.connect(self._on_status)
        self._worker.finished.connect(self._on_download_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_status(self, msg: str):
        self._log.append(msg)

    def _on_download_finished(self):
        self.progress.setVisible(False)
        self.label_status.setText("Modèle prêt !")
        self.model_ready.emit()

    def _on_error(self, msg: str):
        self.progress.setVisible(False)
        self.label_status.setText("Erreur lors du téléchargement.")
        self._log.append(f"[ERREUR] {msg}")
        self.btn_start.setEnabled(True)
