from datetime import datetime
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QFrame, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QTableWidget, QTableWidgetItem, QFileDialog,
                               QMessageBox, QTreeWidget, QTreeWidgetItem, QLineEdit)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt
from anonymator.ui.components.grid import paint_grid
from anonymator.ui.theme import color
from anonymator.files.anonymize_file import (anonymize_file, UnsupportedFormat, FileResult)
from anonymator.files import csv_io
from anonymator.output_naming import anonymized_path
from anonymator.files.columns import default_maskable_columns
from anonymator.core.file_review_session import FileReviewSession
from anonymator.ui.file_scan_worker import FileScanWorker
from anonymator.ui.file_anonymize_worker import FileAnonymizeWorker
from anonymator.ui.colors import color_for
from anonymator.ui.icons import icon
from anonymator.ui.components.header import HeaderBand
from anonymator.ui.components.nav_band import NavBand
from anonymator.ui.components.cards import Card
from anonymator.core.model_status import is_model_available
from anonymator.ner import NullNer
from anonymator.ui.model_loader import ModelLoader
from anonymator.ui.components.banner import ModelBanner

PAGE_SIZE = 20


def _fmt_int(n: int) -> str:
    return f"{n:,}".replace(",", " ")   # espace fine insécable


class FileScreen(QWidget):
    def __init__(self, ref, loader, prefs, on_back, on_text_review=None, on_request_model=None):
        super().__init__()
        self.setObjectName("FileBg")
        self.setStyleSheet(f"#FileBg {{ background: {color('grid_bg')}; }}")
        self.ref, self.loader, self.prefs = ref, loader, prefs
        self.on_text_review = on_text_review
        self.on_request_model = on_request_model
        self.path: Path | None = None
        self.doc = None
        self.session: FileReviewSession | None = None
        self.page = 0
        self._busy = False
        self._degraded = False
        self._worker: FileScanWorker | None = None
        self._anon_worker: FileAnonymizeWorker | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)
        root.addWidget(HeaderBand())
        root.addWidget(NavBand("Fichier", "folder", on_home=on_back))

        self.banner = ModelBanner(on_install=self._request_model)
        root.addWidget(self.banner)

        # ---- barre d'action : infos fichier (gauche) + actions (droite) ----
        bar = QHBoxLayout(); bar.setContentsMargins(18, 14, 18, 8); bar.setSpacing(12)
        self._file_ic = QLabel(); self._file_ic.setPixmap(icon("document", "#00965E").pixmap(22, 22))
        info_col = QVBoxLayout(); info_col.setSpacing(1)
        self.name_label = QLabel("Aucun fichier"); self.name_label.setObjectName("fileName")
        self.meta_label = QLabel("Importez un fichier .txt, .csv ou .xlsx")
        self.meta_label.setObjectName("fileMeta")
        info_col.addWidget(self.name_label); info_col.addWidget(self.meta_label)
        bar.addWidget(self._file_ic); bar.addLayout(info_col); bar.addStretch()

        self.btn_open = QPushButton("  Ouvrir"); self.btn_open.setObjectName("navOpen")
        self.btn_open.setIcon(icon("folder", "white")); self.btn_open.clicked.connect(self._open)
        self.btn_review = QPushButton("  Analyser"); self.btn_review.setObjectName("primary")
        self.btn_review.setIcon(icon("scan", "white"))
        self.btn_review.setEnabled(False); self.btn_review.clicked.connect(self.analyze)
        self.btn_run = QPushButton("  Anonymiser && enregistrer"); self.btn_run.setObjectName("info")
        self.btn_run.setIcon(icon("shield", "white")); self.btn_run.clicked.connect(self._run_clicked)
        for b in (self.btn_open, self.btn_review, self.btn_run):
            bar.addWidget(b)
        action_band = QFrame(); action_band.setObjectName("ActionBand")
        action_band.setLayout(bar)
        root.addWidget(action_band)

        # ---- corps : extrait (gauche) + entités (droite) ----
        self.table = QTableWidget()
        self.table.setShowGrid(True)
        self.table.setAlternatingRowColors(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setDefaultAlignment(Qt.AlignCenter)
        table_card = Card("document", "Écritures comptables — extrait")
        table_card.body.addWidget(self.table)

        from PySide6.QtWidgets import QHeaderView
        self.side = QTreeWidget()
        self.side.setHeaderHidden(True)
        self.side.setColumnCount(2)
        self.side.setRootIsDecorated(True)
        self.side.header().setStretchLastSection(False)
        self.side.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.side.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.side.itemChanged.connect(self._on_side_changed)
        ent_card = Card("shield", "Entités détectées")
        self.occ_badge = QLabel(""); self.occ_badge.setObjectName("occBadge"); self.occ_badge.hide()
        ent_card.head.addWidget(self.occ_badge)
        hint = QLabel("Décochez une valeur ou une catégorie pour la conserver en clair.")
        hint.setObjectName("hint"); hint.setWordWrap(True)
        ent_card.body.addWidget(hint)
        ent_card.body.addWidget(self.side)
        self.side.hide(); hint.hide(); self._hint = hint

        body = QHBoxLayout(); body.setContentsMargins(18, 0, 18, 8); body.setSpacing(12)
        body.addWidget(table_card, 3)
        body.addWidget(ent_card, 2)
        root.addLayout(body, 1)

        # ---- pied de pagination ----
        self.pager = QHBoxLayout(); self.pager.setContentsMargins(18, 6, 18, 14)
        self.btn_first = QPushButton("« Première"); self.btn_first.setObjectName("pager")
        self.btn_first.clicked.connect(lambda: self._go(0))
        self.btn_prev = QPushButton("‹ Précédent"); self.btn_prev.setObjectName("pager")
        self.btn_prev.clicked.connect(lambda: self._go(self.page - 1))
        self.lbl_page = QLabel(""); self.lbl_page.setObjectName("pageInfo")
        self.lbl_page.setAlignment(Qt.AlignCenter)
        self.btn_next = QPushButton("Suivant ›"); self.btn_next.setObjectName("pager")
        self.btn_next.clicked.connect(lambda: self._go(self.page + 1))
        self.btn_last = QPushButton("Dernière »"); self.btn_last.setObjectName("pager")
        self.btn_last.clicked.connect(lambda: self._go(self._page_count() - 1))
        self.goto = QLineEdit(); self.goto.setFixedWidth(50); self.goto.setPlaceholderText("page")
        self.goto.returnPressed.connect(self._goto_typed)
        self.pager.addWidget(self.btn_first); self.pager.addWidget(self.btn_prev)
        self.pager.addStretch(); self.pager.addWidget(self.lbl_page); self.pager.addStretch()
        self.pager.addWidget(self.btn_next); self.pager.addWidget(self.btn_last)
        self.pager.addWidget(self.goto)
        self.pager_widget = QWidget(); self.pager_widget.setObjectName("PagerBar")
        self.pager_widget.setLayout(self.pager); self.pager_widget.hide()
        root.addWidget(self.pager_widget)

        # Voile "travail en cours" superposé (masqué par défaut)
        self._overlay = QLabel("⏳  Analyse en cours…", self)
        self._overlay.setObjectName("busyOverlay")
        self._overlay.setAlignment(Qt.AlignCenter)
        self._overlay.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._overlay.isVisible():
            self._overlay.setGeometry(self.rect())

    def paintEvent(self, _event):
        paint_grid(self)

    # ---------- file-info meta ----------
    def _set_meta(self, status: str | None = None):
        if not self.path:
            self.name_label.setText("Aucun fichier")
            self.meta_label.setText("Importez un fichier .txt, .csv ou .xlsx")
            return
        self.name_label.setText(self.path.name)
        kind = f"Fichier {self.path.suffix.lstrip('.').upper()}"
        parts = [kind]
        if self.doc is not None:
            parts.append(f"{_fmt_int(len(self.doc.rows))} lignes")
        if status is not None:
            parts.append(status)
        elif self.session is not None:
            parts.append(f"{_fmt_int(self.session.total_occurrences())} entités détectées")
        self.meta_label.setText(" · ".join(parts))

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
        self.occ_badge.hide(); self._hint.hide()
        suffix = self.path.suffix.lower()
        self.btn_review.setEnabled(suffix in (".csv", ".txt"))
        if suffix == ".csv":
            self.doc = csv_io.read_csv(self.path)
            self._fill_preview(self.doc.rows[:50])
        self._set_meta()

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

    def _run_clicked(self):
        """Handler du bouton : anonymise, écrit et confirme à l'utilisateur."""
        if not self.path:
            QMessageBox.information(self, "Aucun fichier",
                                    "Ouvrez d'abord un fichier à anonymiser.")
            return
        if self.session is not None:
            # Revue déjà faite : masquage synchrone (léger, aucun modèle requis).
            result = self.run()
            if result is not None:
                QMessageBox.information(
                    self, "Fichier anonymisé",
                    f"Fichier enregistré :\n{result.output_path}")
            return
        # Sans revue : construction du détecteur + anonymisation hors thread UI
        # (overlay pendant le chargement, échec remonté via `error`).
        if self._anon_worker and self._anon_worker.isRunning():
            return
        out_dir = Path(self.prefs.output_dir) if self.prefs.output_dir else self.path.parent
        self._degraded = not (self.loader.has_detector() or is_model_available())
        loader = ModelLoader(NullNer()) if self._degraded else self.loader
        self._set_busy(True)
        self._anon_worker = FileAnonymizeWorker(
            self.path, loader, self.ref, out_dir, datetime.now())
        self._anon_worker.done.connect(self._on_anonymized)
        self._anon_worker.error.connect(self._on_run_error)
        self._anon_worker.finished.connect(self._anon_worker.deleteLater)
        self._anon_worker.start()

    def _on_anonymized(self, result):
        self._set_busy(False)
        self.banner.setVisible(self._degraded)
        QMessageBox.information(
            self, "Fichier anonymisé",
            f"Fichier enregistré :\n{result.output_path}")

    def _on_run_error(self, msg):
        self._set_busy(False)
        QMessageBox.warning(self, "Anonymisation impossible", msg)

    # ---------- review mode ----------
    def analyze(self):
        if self._worker and self._worker.isRunning():
            return
        if self.path and self.path.suffix.lower() == ".txt":
            from anonymator.files import txt_io
            text, _enc = txt_io.read_text(self.path)
            if self.on_text_review:
                self.on_text_review(text)
            return
        if self.doc is None:
            return
        cols = default_maskable_columns(self.doc.rows, self.doc.has_header)
        self._cols = cols
        self._degraded = not (self.loader.has_detector() or is_model_available())
        # Le détecteur est construit DANS le worker (pas ici, sur le thread UI) :
        # une construction lente affiche l'overlay, un échec remonte via `error`.
        loader = ModelLoader(NullNer()) if self._degraded else self.loader
        self._set_busy(True)
        self._worker = FileScanWorker(self.doc, loader, self.ref, cols)
        self._worker.scan_finished.connect(self._on_scanned)
        self._worker.error.connect(self._on_scan_error)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.start()

    def _set_busy(self, busy: bool):
        self._busy = busy
        self.btn_review.setEnabled(not busy)
        self.btn_run.setEnabled(not busy)
        self.btn_open.setEnabled(not busy)
        if busy:
            self._overlay.setGeometry(self.rect())
            self._overlay.raise_(); self._overlay.show()
            self.setCursor(Qt.BusyCursor)
        else:
            self._overlay.hide()
            self.setCursor(Qt.ArrowCursor)
        self._set_meta("analyse en cours…" if busy else None)

    def _on_scan_error(self, msg):
        self._set_busy(False)
        QMessageBox.warning(self, "Erreur d'analyse", msg)

    def _on_scanned(self, scanned):
        self.session = FileReviewSession(self.doc, scanned, self.ref, self._cols)
        self._set_busy(False)
        self.banner.setVisible(self._degraded)
        self.occ_badge.setText(f"{_fmt_int(self.session.total_occurrences())} occ.")
        self.occ_badge.show(); self._hint.show()
        self.page = 0
        self._build_side()
        self.side.show(); self.pager_widget.show()
        self._render_page()

    def _build_side(self):
        from PySide6.QtGui import QFont
        bold = QFont(); bold.setBold(True)
        self.side.blockSignals(True)
        self.side.clear()
        for t in self.session.types():
            top = QTreeWidgetItem([t, f"×{self.session.count_retained(t)}"])
            top.setForeground(0, QColor(color_for(t)))
            top.setForeground(1, QColor("#6B7C72"))
            top.setTextAlignment(1, Qt.AlignRight | Qt.AlignVCenter)
            top.setFont(0, bold)
            top.setData(0, Qt.UserRole, ("type", t, None))
            top.setFlags(top.flags() | Qt.ItemIsUserCheckable)
            top.setCheckState(0, Qt.Checked if self.session.is_type_enabled(t) else Qt.Unchecked)
            for value, n in self.session.values_for(t):
                child = QTreeWidgetItem([value, f"×{n}"])
                child.setForeground(1, QColor("#9aa8a0"))
                child.setTextAlignment(1, Qt.AlignRight | Qt.AlignVCenter)
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
            top.setText(1, f"×{self.session.count_retained(t)}")

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
        last = self._page_count() - 1
        self.lbl_page.setText(f"Page {self.page + 1} / {self._page_count()}")
        self.btn_first.setEnabled(self.page > 0)
        self.btn_prev.setEnabled(self.page > 0)
        self.btn_next.setEnabled(self.page < last)
        self.btn_last.setEnabled(self.page < last)

    def _request_model(self):
        if self.on_request_model is not None:
            self.on_request_model()

    def hide_degraded(self):
        self._degraded = False
        self.banner.setVisible(False)
