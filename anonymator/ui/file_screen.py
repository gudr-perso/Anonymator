from datetime import datetime
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QTableWidget, QTableWidgetItem, QFileDialog,
                               QMessageBox)
from anonymator.files.anonymize_file import anonymize_file, UnsupportedFormat
from anonymator.files import csv_io


class FileScreen(QWidget):
    def __init__(self, ref, loader, prefs, on_back):
        super().__init__()
        self.ref, self.loader, self.prefs = ref, loader, prefs
        self.path: Path | None = None
        self.excluded: set[int] = set()
        layout = QVBoxLayout(self)
        self.label = QLabel("Aucun fichier")
        self.table = QTableWidget()
        btns = QHBoxLayout()
        self.btn_open = QPushButton("Ouvrir…")
        self.btn_open.clicked.connect(self._open)
        self.btn_run = QPushButton("Anonymiser et enregistrer")
        self.btn_run.clicked.connect(lambda: self.run())
        self.btn_back = QPushButton("Accueil")
        self.btn_back.setObjectName("ghost")
        self.btn_back.clicked.connect(on_back)
        for b in (self.btn_open, self.btn_run, self.btn_back):
            btns.addWidget(b)
        layout.addWidget(self.label)
        layout.addLayout(btns)
        layout.addWidget(self.table)

    def _open(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Ouvrir", "", "Fichiers (*.txt *.csv *.xlsx)")
        if path:
            self.load_path(path)

    def load_path(self, path: str):
        self.path = Path(path)
        self.excluded = set()
        self.label.setText(self.path.name)
        if self.path.suffix.lower() == ".csv":
            doc = csv_io.read_csv(self.path)
            self._fill_preview(doc.rows[:50])

    def _fill_preview(self, rows):
        if not rows:
            return
        self.table.setColumnCount(max(len(r) for r in rows))
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                self.table.setItem(r, c, QTableWidgetItem(val))

    def run(self, when: datetime | None = None):
        if not self.path:
            return None
        out_dir = Path(self.prefs.output_dir) if self.prefs.output_dir else self.path.parent
        when = when or datetime.now()
        try:
            ner = self.loader.get()
            exclude = self.excluded if self.path.suffix.lower() == ".csv" else None
            result = anonymize_file(self.path, ner, self.ref, out_dir, when,
                                    exclude=exclude)
        except UnsupportedFormat as e:
            QMessageBox.warning(self, "Format non supporté", str(e))
            return None
        return result
