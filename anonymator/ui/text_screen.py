from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QTextEdit, QLabel, QFileDialog, QApplication,
                               QScrollArea, QMessageBox)
from PySide6.QtGui import QTextCharFormat, QColor, QTextCursor
from PySide6.QtCore import Qt
from anonymator.core.review_session import ReviewSession
from anonymator.core.risk import risk_level
from anonymator.ui.colors import color_for
from anonymator.ui.icons import icon
from anonymator.ui.text_analyze_worker import TextAnalyzeWorker
from anonymator.ui.components.header import HeaderBand
from anonymator.ui.components.cards import Card, StatCard
from anonymator.ui.components.badge import CategoryBadge
from anonymator.ui.components.toggle import ToggleSwitch


class TextScreen(QWidget):
    def __init__(self, ref, loader, prefs, on_back):
        super().__init__()
        self.ref, self.loader, self.prefs = ref, loader, prefs
        self.session: ReviewSession | None = None
        self._worker: TextAnalyzeWorker | None = None

        root = QVBoxLayout(self)
        root.addWidget(HeaderBand())

        crumb = QWidget(); crumb.setObjectName("Crumb")
        cb = QHBoxLayout(crumb); cb.setContentsMargins(4, 4, 4, 4); cb.setSpacing(4)
        home_btn = QPushButton(" Accueil"); home_btn.setObjectName("crumb")
        home_btn.setIcon(icon("home", "#6B7C72")); home_btn.clicked.connect(on_back)
        txt_btn = QPushButton(" Texte"); txt_btn.setObjectName("crumbActive")
        txt_btn.setIcon(icon("document", "#00965E"))
        cb.addWidget(home_btn); cb.addWidget(txt_btn)
        nav = QHBoxLayout(); nav.addWidget(crumb); nav.addStretch()
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
        self.entity_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._entity_host = QWidget(); self._entity_layout = QVBoxLayout(self._entity_host)
        self._entity_layout.addStretch()
        self.entity_area.setWidget(self._entity_host)
        ent_card.body.addWidget(self.entity_area)

        body.addLayout(left, 3); body.addWidget(ent_card, 2)
        root.addLayout(body)

        actions = QHBoxLayout()
        self.btn_analyze = QPushButton("  Analyser"); self.btn_analyze.setObjectName("primary")
        self.btn_analyze.setIcon(icon("scan", "white"))
        self.btn_analyze.clicked.connect(self.analyze)
        self.btn_apply = QPushButton("  Appliquer le masquage"); self.btn_apply.setObjectName("info")
        self.btn_apply.setIcon(icon("sparkle", "white"))
        self.btn_apply.clicked.connect(self.apply)
        self.btn_copy = QPushButton("Copier"); self.btn_copy.setObjectName("ghost"); self.btn_copy.clicked.connect(self._copy)
        self.btn_export = QPushButton("Exporter .txt"); self.btn_export.setObjectName("ghost"); self.btn_export.clicked.connect(self._export)
        actions.addWidget(self.btn_analyze); actions.addWidget(self.btn_apply); actions.addStretch()
        actions.addWidget(self.btn_copy); actions.addWidget(self.btn_export)
        root.addLayout(actions)

        # Voile "travail en cours" superposé (masqué par défaut)
        self._overlay = QLabel("⏳  Analyse en cours…", self)
        self._overlay.setObjectName("busyOverlay")
        self._overlay.setAlignment(Qt.AlignCenter)
        self._overlay.hide()

    def analyze(self):
        if self._worker is not None and self._worker.isRunning():
            return
        text = self.input.toPlainText()
        self._set_busy(True)
        self._worker = TextAnalyzeWorker(text, self.loader, self.ref)
        self._worker.done.connect(self._on_analyzed)
        self._worker.error.connect(self._on_analyze_error)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.start()

    def _on_analyzed(self, text, ents):
        self.session = ReviewSession(text, ents)
        self._refresh_entities(); self._highlight(); self._refresh_stats()
        self._set_busy(False)

    def _on_analyze_error(self, msg):
        self._set_busy(False)
        QMessageBox.warning(self, "Erreur d'analyse", msg)

    def _set_busy(self, busy: bool, message: str = "⏳  Analyse en cours…"):
        if busy:
            self._overlay.setText(message)
            self._overlay.setGeometry(self.rect())
            self._overlay.raise_(); self._overlay.show()
            self.setCursor(Qt.BusyCursor)
        else:
            self._overlay.hide()
            self.unsetCursor()
        self.btn_analyze.setEnabled(not busy)
        self.btn_apply.setEnabled(not busy)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._overlay.isVisible():
            self._overlay.setGeometry(self.rect())

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
            col = QVBoxLayout(); col.setContentsMargins(0, 0, 0, 0); col.setSpacing(1)
            val = QLabel(e.value); val.setStyleSheet("font-size: 13px;")
            col.addWidget(val)
            if not e.confirmed:
                note = QLabel("⚠ format ressemblant mais erroné")
                note.setStyleSheet("color:#9a031e; font-style:italic; font-size:11px;")
                note.setToolTip("Le motif a la bonne forme mais la validation "
                                "(clé de contrôle) a échoué — non masqué par défaut.")
                col.addWidget(note)
            h.addLayout(col); h.addStretch()
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
