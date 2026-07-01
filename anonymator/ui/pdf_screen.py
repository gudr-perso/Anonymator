# anonymator/ui/pdf_screen.py
from datetime import datetime
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QFileDialog, QMessageBox, QTreeWidget,
                               QTreeWidgetItem, QHeaderView)
from PySide6.QtGui import QColor, QFont
from PySide6.QtCore import Qt
from anonymator.files.pdf import pdf_io
from anonymator.files.pdf.extract import (
    ScannedPdfNotSupported, EncryptedPdfError, CorruptPdfError)
from anonymator.files.pdf.render import RENDER_ZOOM
from anonymator.files.anonymize_file import FileResult
from anonymator.core.pdf_review_session import PdfReviewSession
from anonymator.ui.pdf_scan_worker import PdfScanWorker
from anonymator.ui.pdf_canvas import PdfCanvas
from anonymator.ui.colors import color_for
from anonymator.ui.icons import icon
from anonymator.ui.components.header import HeaderBand
from anonymator.ui.components.cards import Card
from anonymator.ui.components.banner import ModelBanner
from anonymator.core.model_status import is_model_available
from anonymator.ner import NullNer


class PdfScreen(QWidget):
    def __init__(self, ref, loader, prefs, on_back, on_request_model=None):
        super().__init__()
        self.ref, self.loader, self.prefs = ref, loader, prefs
        self.on_request_model = on_request_model
        self.path: Path | None = None
        self.session: PdfReviewSession | None = None
        self.page = 0
        self._page_count = 0
        self._busy = False
        self._degraded = False
        self._worker: PdfScanWorker | None = None
        self._png_cache: dict[int, bytes] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)
        root.addWidget(HeaderBand())
        self.banner = ModelBanner(on_install=self._request_model)
        root.addWidget(self.banner)

        # ---- barre d'action ----
        bar = QHBoxLayout(); bar.setContentsMargins(18, 14, 18, 8); bar.setSpacing(12)
        self._file_ic = QLabel(); self._file_ic.setPixmap(icon("document", "#00965E").pixmap(22, 22))
        info_col = QVBoxLayout(); info_col.setSpacing(1)
        self.name_label = QLabel("Aucun PDF"); self.name_label.setObjectName("fileName")
        self.meta_label = QLabel("Importez un fichier .pdf natif (texte sélectionnable)")
        self.meta_label.setObjectName("fileMeta")
        info_col.addWidget(self.name_label); info_col.addWidget(self.meta_label)
        bar.addWidget(self._file_ic); bar.addLayout(info_col); bar.addStretch()

        self.btn_open = QPushButton("  Ouvrir"); self.btn_open.setObjectName("ghost")
        self.btn_open.setIcon(icon("folder", "#00965E")); self.btn_open.clicked.connect(self._open)
        self.btn_review = QPushButton("  Analyser"); self.btn_review.setObjectName("primary")
        self.btn_review.setIcon(icon("scan", "white"))
        self.btn_review.setEnabled(False); self.btn_review.clicked.connect(self.analyze)
        self.btn_zone = QPushButton("  Zone manuelle"); self.btn_zone.setObjectName("ghost")
        self.btn_zone.setCheckable(True); self.btn_zone.setIcon(icon("scan", "#6B7C72"))
        self.btn_zone.toggled.connect(self._toggle_zone)
        self.btn_redact = QPushButton("  Caviarder (PDF)"); self.btn_redact.setObjectName("info")
        self.btn_redact.setIcon(icon("shield", "white")); self.btn_redact.clicked.connect(self._redact_clicked)
        self.btn_text = QPushButton("  Extraire en .txt"); self.btn_text.setObjectName("ghost")
        self.btn_text.setIcon(icon("document", "#6B7C72")); self.btn_text.clicked.connect(self._text_clicked)
        self.btn_back = QPushButton("  Accueil"); self.btn_back.setObjectName("ghost")
        self.btn_back.setIcon(icon("home", "#6B7C72")); self.btn_back.clicked.connect(on_back)
        for b in (self.btn_open, self.btn_review, self.btn_zone,
                  self.btn_redact, self.btn_text, self.btn_back):
            bar.addWidget(b)
        root.addLayout(bar)

        # ---- corps : canevas (gauche) + entités (droite) ----
        self.canvas = PdfCanvas()
        self.canvas.manual_rect_drawn.connect(self._on_manual_rect)
        canvas_card = Card("document", "Aperçu de la page")
        canvas_card.body.addWidget(self.canvas)

        self.side = QTreeWidget()
        self.side.setHeaderHidden(True); self.side.setColumnCount(2)
        self.side.setRootIsDecorated(True)
        self.side.header().setStretchLastSection(False)
        self.side.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.side.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.side.itemChanged.connect(self._on_side_changed)
        ent_card = Card("shield", "Entités détectées")
        hint = QLabel("Décochez pour conserver en clair. Bouton « Zone manuelle » "
                      "pour caviarder un tampon/signature non détecté.")
        hint.setObjectName("hint"); hint.setWordWrap(True)
        ent_card.body.addWidget(hint); ent_card.body.addWidget(self.side)
        self.side.hide()

        body = QHBoxLayout(); body.setContentsMargins(18, 0, 18, 8); body.setSpacing(12)
        body.addWidget(canvas_card, 3); body.addWidget(ent_card, 2)
        root.addLayout(body, 1)

        # ---- pagination ----
        self.pager = QHBoxLayout(); self.pager.setContentsMargins(18, 6, 18, 14)
        self.btn_prev = QPushButton("‹ Précédent"); self.btn_prev.setObjectName("pager")
        self.btn_prev.clicked.connect(lambda: self._go(self.page - 1))
        self.lbl_page = QLabel(""); self.lbl_page.setObjectName("pageInfo")
        self.lbl_page.setAlignment(Qt.AlignCenter)
        self.btn_next = QPushButton("Suivant ›"); self.btn_next.setObjectName("pager")
        self.btn_next.clicked.connect(lambda: self._go(self.page + 1))
        self.pager.addWidget(self.btn_prev); self.pager.addStretch()
        self.pager.addWidget(self.lbl_page); self.pager.addStretch()
        self.pager.addWidget(self.btn_next)
        self.pager_widget = QWidget(); self.pager_widget.setLayout(self.pager); self.pager_widget.hide()
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

    # ---------- ouverture ----------
    def _open(self):
        path, _ = QFileDialog.getOpenFileName(self, "Ouvrir un PDF", "", "PDF (*.pdf)")
        if path:
            self.load_path(path)

    def load_path(self, path: str):
        self.path = Path(path)
        self.session = None
        self._png_cache = {}
        self.side.hide(); self.pager_widget.hide()
        self.btn_zone.setChecked(False)
        self.btn_review.setEnabled(self.path.suffix.lower() == ".pdf")
        self.name_label.setText(self.path.name)
        self.meta_label.setText("Fichier PDF — cliquez « Analyser »")

    # ---------- analyse ----------
    def analyze(self):
        if self._worker and self._worker.isRunning():
            return
        if not self.path:
            return
        self._degraded = not (self.loader.has_detector() or is_model_available())
        ner = NullNer() if self._degraded else self.loader.get()
        self._set_busy(True)
        self._worker = PdfScanWorker(self.path, ner, self.ref)
        self._worker.scan_finished.connect(self._on_scanned)
        self._worker.error.connect(self._on_scan_error)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.start()

    def _set_busy(self, busy: bool):
        self._busy = busy
        for b in (self.btn_review, self.btn_redact, self.btn_text, self.btn_open):
            b.setEnabled(not busy)
        if busy:
            self._overlay.setGeometry(self.rect())
            self._overlay.raise_(); self._overlay.show()
            self.setCursor(Qt.BusyCursor)
        else:
            self._overlay.hide()
            self.setCursor(Qt.ArrowCursor)

    def _on_scan_error(self, msg):
        self._set_busy(False)
        QMessageBox.warning(self, "PDF non exploitable", msg)

    def _on_scanned(self, pages):
        self.session = PdfReviewSession(pages, self.ref)
        self._page_count = len(pages)
        self._set_busy(False)
        self.banner.setVisible(self._degraded)
        self.page = 0
        self._build_side()
        self.side.show()
        self.pager_widget.setVisible(self._page_count > 1)
        self._render_page()

    # ---------- panneau latéral (même structure que FileScreen) ----------
    def _build_side(self):
        bold = QFont(); bold.setBold(True)
        self.side.blockSignals(True); self.side.clear()
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
                child.setCheckState(0, Qt.Checked if self.session.is_value_enabled(t, value) else Qt.Unchecked)
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

    # ---------- rendu page + overlays ----------
    def _png_for(self, page_index: int) -> bytes:
        if page_index not in self._png_cache:
            self._png_cache[page_index] = pdf_io.render_page_at(self.path, page_index)
        return self._png_cache[page_index]

    def _render_page(self):
        if self.session is None:
            return
        self.canvas.set_page(self._png_for(self.page), RENDER_ZOOM)
        self.canvas.set_overlays(self.session.retained_entity_rects(self.page),
                                 self.session.manual_rects(self.page))
        self.lbl_page.setText(f"Page {self.page + 1} / {self._page_count}")
        self.btn_prev.setEnabled(self.page > 0)
        self.btn_next.setEnabled(self.page < self._page_count - 1)

    def _go(self, page: int):
        self.page = max(0, min(page, self._page_count - 1))
        self._render_page()

    # ---------- zone manuelle ----------
    def _toggle_zone(self, on: bool):
        self.canvas.set_draw_mode(on)

    def _on_manual_rect(self, rect: tuple):
        if self.session is not None:
            self.session.add_manual_rect(self.page, rect)
            self._render_page()

    # ---------- exécution ----------
    def run_redact(self, when: datetime | None = None) -> FileResult | None:
        if self.session is None or not self.path:
            return None
        out_dir = Path(self.prefs.output_dir) if self.prefs.output_dir else self.path.parent
        when = when or datetime.now()
        rects = self.session.retained_rects_by_page()
        out = pdf_io.anonymize_pdf_redact(self.path, rects, out_dir, when)
        return FileResult(out, self.session.report())

    def run_text(self, when: datetime | None = None) -> FileResult | None:
        if not self.path:
            return None
        out_dir = Path(self.prefs.output_dir) if self.prefs.output_dir else self.path.parent
        when = when or datetime.now()
        try:
            ner = self.loader.get()
            return pdf_io.anonymize_pdf_text(self.path, ner, self.ref, out_dir, when)
        except (ScannedPdfNotSupported, EncryptedPdfError, CorruptPdfError) as e:
            QMessageBox.warning(self, "PDF non exploitable", str(e))
            return None

    def _redact_clicked(self):
        if self.session is None:
            QMessageBox.information(self, "Analysez d'abord",
                                    "Cliquez « Analyser » avant de caviarder.")
            return
        confirm = QMessageBox.question(
            self, "Confirmer la rédaction",
            "La rédaction détruit définitivement les données sélectionnées "
            "dans le PDF de sortie. Continuer ?")
        if confirm != QMessageBox.Yes:
            return
        res = self.run_redact()
        if res is not None:
            QMessageBox.information(self, "PDF caviardé",
                                    f"Fichier enregistré :\n{res.output_path}")

    def _text_clicked(self):
        if not self.path:
            QMessageBox.information(self, "Aucun PDF", "Ouvrez d'abord un PDF.")
            return
        res = self.run_text()
        if res is not None:
            QMessageBox.information(self, "Texte extrait",
                                    f"Fichier enregistré :\n{res.output_path}")

    def _request_model(self):
        if self.on_request_model is not None:
            self.on_request_model()

    def hide_degraded(self):
        self._degraded = False
        self.banner.setVisible(False)
