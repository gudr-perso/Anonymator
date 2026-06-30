from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QTextEdit, QListWidget, QListWidgetItem, QLabel,
                               QFileDialog, QApplication)
from PySide6.QtGui import QTextCharFormat, QColor, QTextCursor
from PySide6.QtCore import Qt
from anonymator.core.chunking import detect_long
from anonymator.core.review_session import ReviewSession
from anonymator.ui.colors import color_for


class TextScreen(QWidget):
    def __init__(self, ref, loader, prefs, on_back):
        super().__init__()
        self.ref, self.loader, self.prefs = ref, loader, prefs
        self.session: ReviewSession | None = None
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Texte à anonymiser"))
        self.input = QTextEdit()
        self.entity_list = QListWidget()
        self.output = QTextEdit(); self.output.setReadOnly(True)
        btns = QHBoxLayout()
        self.btn_analyze = QPushButton("Analyser"); self.btn_analyze.clicked.connect(self.analyze)
        self.btn_apply = QPushButton("Appliquer le masquage"); self.btn_apply.clicked.connect(self.apply)
        self.btn_copy = QPushButton("Copier"); self.btn_copy.setObjectName("ghost"); self.btn_copy.clicked.connect(self._copy)
        self.btn_export = QPushButton("Exporter .txt"); self.btn_export.setObjectName("ghost"); self.btn_export.clicked.connect(self._export)
        self.btn_back = QPushButton("Accueil"); self.btn_back.setObjectName("ghost"); self.btn_back.clicked.connect(on_back)
        for b in (self.btn_analyze, self.btn_apply, self.btn_copy, self.btn_export, self.btn_back):
            btns.addWidget(b)
        layout.addWidget(self.input)
        layout.addWidget(QLabel("Entités détectées (décocher = ne pas masquer)"))
        layout.addWidget(self.entity_list)
        layout.addLayout(btns)
        layout.addWidget(QLabel("Résultat"))
        layout.addWidget(self.output)
        self.entity_list.itemChanged.connect(self._on_item_changed)

    def analyze(self):
        text = self.input.toPlainText()
        ner = self.loader.get()
        ents = detect_long(text, ner, self.ref)
        self.session = ReviewSession(text, ents)
        self._refresh_list(); self._highlight()

    def _refresh_list(self):
        self.entity_list.blockSignals(True)
        self.entity_list.clear()
        for i, e in enumerate(self.session.entities()):
            item = QListWidgetItem(f"{e.type} — {e.value}")
            item.setData(Qt.UserRole, i)
            item.setForeground(QColor(color_for(e.type)))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.entity_list.addItem(item)
        self.entity_list.blockSignals(False)

    def _on_item_changed(self, item):
        idx = item.data(Qt.UserRole)
        self.session.set_entity_enabled(idx, item.checkState() == Qt.Checked)
        self._highlight()

    def _highlight(self):
        retained = set(id(e) for e in self.session.retained())
        cursor_doc = self.input.document()
        extra = []
        for e in self.session.entities():
            if id(e) not in retained:
                continue
            fmt = QTextCharFormat()
            c = QColor(color_for(e.type)); c.setAlpha(70)
            fmt.setBackground(c)
            cur = QTextCursor(cursor_doc)
            cur.setPosition(e.start); cur.setPosition(e.end, QTextCursor.KeepAnchor)
            sel = QTextEdit.ExtraSelection(); sel.cursor = cur; sel.format = fmt
            extra.append(sel)
        self.input.setExtraSelections(extra)

    def apply(self):
        self.output.setPlainText(self.session.masked_text(self.ref))

    def _copy(self):
        QApplication.clipboard().setText(self.output.toPlainText())

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exporter", "anonymise.txt", "*.txt")
        if path:
            from pathlib import Path
            Path(path).write_text(self.output.toPlainText(), encoding="utf-8")
