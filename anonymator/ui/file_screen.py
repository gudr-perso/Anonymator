from datetime import datetime
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QTableWidget, QTableWidgetItem, QFileDialog,
                               QMessageBox, QTreeWidget, QTreeWidgetItem, QLineEdit)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt
from anonymator.files.anonymize_file import (anonymize_file, UnsupportedFormat)
from anonymator.files import csv_io
from anonymator.files.columns import default_maskable_columns
from anonymator.core.file_review_session import FileReviewSession
from anonymator.ui.file_scan_worker import FileScanWorker
from anonymator.ui.colors import color_for

PAGE_SIZE = 20


class FileScreen(QWidget):
    def __init__(self, ref, loader, prefs, on_back, on_text_review=None):
        super().__init__()
        self.ref, self.loader, self.prefs = ref, loader, prefs
        self.on_text_review = on_text_review
        self.path: Path | None = None
        self.doc = None
        self.session: FileReviewSession | None = None
        self.page = 0
        self._worker: FileScanWorker | None = None

        layout = QVBoxLayout(self)
        self.label = QLabel("Aucun fichier")
        self.table = QTableWidget()
        btns = QHBoxLayout()
        self.btn_open = QPushButton("Ouvrir…")
        self.btn_open.clicked.connect(self._open)
        self.btn_review = QPushButton("Analyser et revoir")
        self.btn_review.setEnabled(False)
        self.btn_review.clicked.connect(self.analyze)
        self.btn_run = QPushButton("Anonymiser et enregistrer")
        self.btn_run.clicked.connect(lambda: self.run())
        self.btn_back = QPushButton("Accueil")
        self.btn_back.setObjectName("ghost")
        self.btn_back.clicked.connect(on_back)
        for b in (self.btn_open, self.btn_review, self.btn_run, self.btn_back):
            btns.addWidget(b)

        # side panel (types/values) + pagination — hidden until analyze
        self.side = QTreeWidget()
        self.side.setHeaderLabels(["Typologie / valeur", "Occ."])
        self.side.itemChanged.connect(self._on_side_changed)
        self.side.hide()
        self.pager = QHBoxLayout()
        self.btn_first = QPushButton("« Première"); self.btn_first.clicked.connect(lambda: self._go(0))
        self.btn_prev = QPushButton("‹ Préc."); self.btn_prev.clicked.connect(lambda: self._go(self.page - 1))
        self.lbl_page = QLabel("")
        self.btn_next = QPushButton("Suiv. ›"); self.btn_next.clicked.connect(lambda: self._go(self.page + 1))
        self.btn_last = QPushButton("Dernière »"); self.btn_last.clicked.connect(lambda: self._go(self._page_count() - 1))
        self.goto = QLineEdit(); self.goto.setFixedWidth(50)
        self.goto.returnPressed.connect(self._goto_typed)
        for w in (self.btn_first, self.btn_prev, self.lbl_page, self.btn_next, self.btn_last, QLabel("Aller à"), self.goto):
            self.pager.addWidget(w)
        self.pager_widget = QWidget(); self.pager_widget.setLayout(self.pager); self.pager_widget.hide()

        body = QHBoxLayout()
        body.addWidget(self.table, 3)
        body.addWidget(self.side, 1)

        layout.addWidget(self.label)
        layout.addLayout(btns)
        layout.addLayout(body)
        layout.addWidget(self.pager_widget)

    # ---------- opening / preview ----------
    def _open(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Ouvrir", "", "Fichiers (*.txt *.csv *.xlsx)")
        if path:
            self.load_path(path)

    def load_path(self, path: str):
        self.path = Path(path)
        self.doc = None
        self.session = None
        self.side.hide(); self.pager_widget.hide()
        self.label.setText(self.path.name)
        suffix = self.path.suffix.lower()
        self.btn_review.setEnabled(suffix == ".csv")   # txt/xlsx routing added in Task 7
        if suffix == ".csv":
            self.doc = csv_io.read_csv(self.path)
            self._fill_preview(self.doc.rows[:50])

    def _fill_preview(self, rows):
        if not rows:
            return
        header = rows[0] if (self.doc and self.doc.has_header) else None
        data = rows[1:] if header else rows
        width = max(len(r) for r in rows)
        self.table.clear()
        self.table.setColumnCount(width)
        self.table.setRowCount(len(data))
        if header:
            self.table.setHorizontalHeaderLabels(
                [header[c] if c < len(header) else f"col{c}" for c in range(width)])
        for r, row in enumerate(data):
            for c in range(width):
                self.table.setItem(r, c, QTableWidgetItem(row[c] if c < len(row) else ""))

    def run(self, when: datetime | None = None):
        if not self.path:
            return None
        out_dir = Path(self.prefs.output_dir) if self.prefs.output_dir else self.path.parent
        when = when or datetime.now()
        if self.session is not None:
            from anonymator.output_naming import anonymized_path
            from anonymator.files.anonymize_file import FileResult
            masked = self.session.masked_document()
            report = self.session.report()
            out = anonymized_path(self.path, out_dir, when)
            csv_io.write_csv(masked, out)
            return FileResult(out, report)
        try:
            ner = self.loader.get()
            result = anonymize_file(self.path, ner, self.ref, out_dir, when)
        except UnsupportedFormat as e:
            QMessageBox.warning(self, "Format non supporté", str(e))
            return None
        return result

    # ---------- review mode ----------
    def analyze(self):
        if self.doc is None:
            return
        cols = default_maskable_columns(self.doc.rows, self.doc.has_header)
        self._cols = cols
        self.btn_review.setEnabled(False)
        self.btn_run.setEnabled(False)
        self.label.setText(f"{self.path.name} — analyse en cours…")
        ner = self.loader.get()
        self._worker = FileScanWorker(self.doc, ner, self.ref, cols)
        self._worker.scan_finished.connect(self._on_scanned)
        self._worker.error.connect(self._on_scan_error)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.start()

    def _on_scan_error(self, msg):
        self.btn_review.setEnabled(True); self.btn_run.setEnabled(True)
        self.label.setText(self.path.name)
        QMessageBox.warning(self, "Erreur d'analyse", msg)

    def _on_scanned(self, scanned):
        self.session = FileReviewSession(self.doc, scanned, self.ref, self._cols)
        self.btn_review.setEnabled(True); self.btn_run.setEnabled(True)
        self.label.setText(self.path.name)
        self.page = 0
        self._build_side()
        self.side.show(); self.pager_widget.show()
        self._render_page()

    def _build_side(self):
        self.side.blockSignals(True)
        self.side.clear()
        for t in self.session.types():
            top = QTreeWidgetItem([t, str(self.session.count_retained(t))])
            top.setForeground(0, QColor(color_for(t)))
            top.setData(0, Qt.UserRole, ("type", t, None))
            top.setFlags(top.flags() | Qt.ItemIsUserCheckable)
            top.setCheckState(0, Qt.Checked if self.session.is_type_enabled(t) else Qt.Unchecked)
            for value, n in self.session.values_for(t):
                child = QTreeWidgetItem([value, f"×{n}"])
                child.setData(0, Qt.UserRole, ("value", t, value))
                child.setFlags(child.flags() | Qt.ItemIsUserCheckable)
                enabled = self.session.is_value_enabled(t, value)
                child.setCheckState(0, Qt.Checked if enabled else Qt.Unchecked)
                top.addChild(child)
            self.side.addTopLevelItem(top)
        self.side.expandAll()
        self.side.blockSignals(False)

    def _on_side_changed(self, item, _col):
        if self.session is None:
            return
        kind, etype, value = item.data(0, Qt.UserRole)
        checked = item.checkState(0) == Qt.Checked
        if kind == "type":
            self.session.set_type_enabled(etype, checked)
        else:
            self.session.set_value_enabled(etype, value, checked)
        self._refresh_counts()
        self._render_page()

    def _refresh_counts(self):
        for i in range(self.side.topLevelItemCount()):
            top = self.side.topLevelItem(i)
            _, t, _ = top.data(0, Qt.UserRole)
            top.setText(1, str(self.session.count_retained(t)))

    def _data_rows(self):
        start = 1 if self.doc.has_header else 0
        return list(range(start, len(self.doc.rows)))

    def _page_count(self):
        n = len(self._data_rows())
        return max(1, (n + PAGE_SIZE - 1) // PAGE_SIZE)

    def _go(self, page):
        self.page = max(0, min(page, self._page_count() - 1))
        self._render_page()

    def _goto_typed(self):
        try:
            self._go(int(self.goto.text()) - 1)
        except ValueError:
            pass

    def _render_page(self):
        if self.session is None:
            return
        rows = self._data_rows()
        width = max((len(r) for r in self.doc.rows), default=0)
        page_rows = rows[self.page * PAGE_SIZE:(self.page + 1) * PAGE_SIZE]
        header = self.doc.rows[0] if self.doc.has_header else None
        self.table.clear()
        self.table.setColumnCount(width)
        self.table.setRowCount(len(page_rows))
        if header:
            self.table.setHorizontalHeaderLabels(
                [header[c] if c < len(header) else f"col{c}" for c in range(width)])
        for vr, r in enumerate(page_rows):
            retained_cols = {c: self.session.entities_for_cell(r, c) for c in range(width)}
            for c in range(width):
                val = self.doc.rows[r][c] if c < len(self.doc.rows[r]) else ""
                item = QTableWidgetItem(val)
                ents = retained_cols.get(c) or []
                if ents:
                    col = QColor(color_for(ents[0].type)); col.setAlpha(70)
                    item.setBackground(col)
                self.table.setItem(vr, c, item)
        self.lbl_page.setText(f"page {self.page + 1} / {self._page_count()}")
