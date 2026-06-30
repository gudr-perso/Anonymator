from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QTextEdit, QLabel, QFileDialog, QApplication,
                               QScrollArea)
from PySide6.QtGui import QTextCharFormat, QColor, QTextCursor
from PySide6.QtCore import Qt
from anonymator.core.chunking import detect_long
from anonymator.core.review_session import ReviewSession
from anonymator.core.risk import risk_level
from anonymator.ui.colors import color_for
from anonymator.ui.components.header import HeaderBand
from anonymator.ui.components.cards import Card, StatCard
from anonymator.ui.components.badge import CategoryBadge
from anonymator.ui.components.toggle import ToggleSwitch


class TextScreen(QWidget):
    def __init__(self, ref, loader, prefs, on_back):
        super().__init__()
        self.ref, self.loader, self.prefs = ref, loader, prefs
        self.session: ReviewSession | None = None

        root = QVBoxLayout(self)
        root.addWidget(HeaderBand())

        nav = QHBoxLayout()
        back = QPushButton("Accueil"); back.setObjectName("ghost"); back.clicked.connect(on_back)
        nav.addWidget(back); nav.addWidget(QLabel("Texte")); nav.addStretch()
        root.addLayout(nav)

        stats = QHBoxLayout()
        self.stat_detected = StatCard("shield", "Entités détectées")
        self.stat_categories = StatCard("layers", "Catégories")
        self.stat_mask = StatCard("eye-off", "À masquer")
        self.stat_keep = StatCard("document", "Conservées", "#E8621A")
        self.stat_risk = StatCard("alert", "Niveau de risque", "#9a031e")
        for c in (self.stat_detected, self.stat_categories, self.stat_mask,
                  self.stat_keep, self.stat_risk):
            stats.addWidget(c)
        root.addLayout(stats)

        body = QHBoxLayout()
        left = QVBoxLayout()
        in_card = Card("document", "Texte à anonymiser")
        self.input = QTextEdit()
        in_card.body.addWidget(self.input)
        out_card = Card("shield", "Résultat anonymisé")
        self.output = QTextEdit(); self.output.setReadOnly(True)
        out_card.body.addWidget(self.output)
        left.addWidget(in_card); left.addWidget(out_card)

        ent_card = Card("shield", "Entités détectées")
        self.entity_area = QScrollArea(); self.entity_area.setWidgetResizable(True)
        self._entity_host = QWidget(); self._entity_layout = QVBoxLayout(self._entity_host)
        self._entity_layout.addStretch()
        self.entity_area.setWidget(self._entity_host)
        ent_card.body.addWidget(self.entity_area)

        body.addLayout(left, 3); body.addWidget(ent_card, 2)
        root.addLayout(body)

        actions = QHBoxLayout()
        self.btn_apply = QPushButton("Appliquer le masquage"); self.btn_apply.setObjectName("primary")
        self.btn_apply.clicked.connect(self.apply)
        self.btn_analyze = QPushButton("Analyser"); self.btn_analyze.setObjectName("secondary")
        self.btn_analyze.clicked.connect(self.analyze)
        self.btn_copy = QPushButton("Copier"); self.btn_copy.setObjectName("ghost"); self.btn_copy.clicked.connect(self._copy)
        self.btn_export = QPushButton("Exporter .txt"); self.btn_export.setObjectName("ghost"); self.btn_export.clicked.connect(self._export)
        actions.addWidget(self.btn_apply); actions.addWidget(self.btn_analyze); actions.addStretch()
        actions.addWidget(self.btn_copy); actions.addWidget(self.btn_export)
        root.addLayout(actions)

    def analyze(self):
        text = self.input.toPlainText()
        ner = self.loader.get()
        ents = detect_long(text, ner, self.ref)
        self.session = ReviewSession(text, ents)
        self._refresh_entities(); self._highlight(); self._refresh_stats()

    def _clear_entities(self):
        while self._entity_layout.count() > 1:
            item = self._entity_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _refresh_entities(self):
        self._clear_entities()
        if self.session is None:
            return
        for i, e in enumerate(self.session.entities()):
            row = QWidget(); h = QHBoxLayout(row); h.setContentsMargins(2, 2, 2, 2)
            h.addWidget(CategoryBadge(e.type))
            val = QLabel(e.value); val.setStyleSheet("font-size: 13px;")
            h.addWidget(val); h.addStretch()
            tog = ToggleSwitch(); tog.setChecked(e.confirmed)
            tog.toggled.connect(lambda on, idx=i: self._on_toggle(idx, on))
            h.addWidget(tog)
            self._entity_layout.insertWidget(self._entity_layout.count() - 1, row)

    def _on_toggle(self, idx, on):
        if self.session is not None:
            self.session.set_entity_enabled(idx, on)
            self._highlight(); self._refresh_stats()

    def _highlight(self):
        if self.session is None:
            return
        retained = set(id(e) for e in self.session.retained())
        doc = self.input.document(); extra = []
        for e in self.session.entities():
            if id(e) not in retained:
                continue
            fmt = QTextCharFormat(); c = QColor(color_for(e.type)); c.setAlpha(70)
            fmt.setBackground(c); fmt.setUnderlineColor(QColor(color_for(e.type)))
            fmt.setUnderlineStyle(QTextCharFormat.SingleUnderline)
            cur = QTextCursor(doc); cur.setPosition(e.start)
            cur.setPosition(e.end, QTextCursor.KeepAnchor)
            sel = QTextEdit.ExtraSelection(); sel.cursor = cur; sel.format = fmt
            extra.append(sel)
        self.input.setExtraSelections(extra)

    def _refresh_stats(self):
        if self.session is None:
            return
        ents = self.session.entities(); retained = self.session.retained()
        self.stat_detected.set_value(len(ents))
        self.stat_categories.set_value(len({e.type for e in ents}))
        self.stat_mask.set_value(len(retained))
        self.stat_keep.set_value(len(ents) - len(retained))
        self.stat_risk.set_value(risk_level(retained, self.ref))

    def apply(self):
        if self.session is not None:
            self.output.setPlainText(self.session.masked_text(self.ref))

    def _copy(self):
        QApplication.clipboard().setText(self.output.toPlainText())

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exporter", "anonymise.txt", "*.txt")
        if path:
            Path(path).write_text(self.output.toPlainText(), encoding="utf-8")
