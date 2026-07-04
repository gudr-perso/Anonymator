# anonymator/ui/pdf_screen.py
from datetime import datetime
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QFrame, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QFileDialog, QMessageBox, QTreeWidget,
                               QTreeWidgetItem, QHeaderView)
from PySide6.QtGui import QColor, QFont, QShortcut, QKeySequence
from PySide6.QtCore import Qt
from anonymator.ui.components.grid import paint_grid
from anonymator.ui.theme import color
from anonymator.files.pdf import pdf_io
from anonymator.files.pdf.extract import (
    ScannedPdfNotSupported, EncryptedPdfError, CorruptPdfError)
from anonymator.files.pdf.render import RENDER_ZOOM
from anonymator.files.anonymize_file import FileResult
from anonymator.core.pdf_review_session import PdfReviewSession
from anonymator.ui.pdf_scan_worker import PdfScanWorker
from anonymator.ui.model_loader import ModelLoader
from anonymator.ui.pdf_canvas import PdfCanvas
from anonymator.ui.colors import color_for
from anonymator.ui.icons import icon
from anonymator.ui.components.header import HeaderBand
from anonymator.ui.components.nav_band import NavBand
from anonymator.ui.components.cards import Card
from anonymator.ui.components.banner import ModelBanner
from anonymator.core.model_status import is_model_available
from anonymator.ner import NullNer


class PdfScreen(QWidget):
    def __init__(self, ref, loader, prefs, on_back, on_request_model=None):
        super().__init__()
        self.setObjectName("PdfBg")
        self.setStyleSheet(f"#PdfBg {{ background: {color('grid_bg')}; }}")
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
        root.addWidget(NavBand("PDF", "scan", on_home=on_back))
        root.addSpacing(14)   # laisse respirer le fond quadrillé au-dessus de la barre
        self.banner = ModelBanner(on_install=self._request_model)
        root.addWidget(self.banner)

        # ---- barre d'action ----
        bar = QHBoxLayout(); bar.setContentsMargins(18, 14, 18, 8); bar.setSpacing(12)
        self._file_ic = QLabel(); self._file_ic.setPixmap(icon("document", color("action")).pixmap(22, 22))
        info_col = QVBoxLayout(); info_col.setSpacing(1)
        self.name_label = QLabel("Aucun PDF"); self.name_label.setObjectName("fileName")
        self.meta_label = QLabel("Importez un fichier .pdf natif (texte sélectionnable)")
        self.meta_label.setObjectName("fileMeta")
        info_col.addWidget(self.name_label); info_col.addWidget(self.meta_label)
        bar.addWidget(self._file_ic); bar.addLayout(info_col); bar.addStretch()

        self.btn_open = QPushButton("  Ouvrir"); self.btn_open.setObjectName("navOpen")
        self.btn_open.setIcon(icon("folder", "white")); self.btn_open.clicked.connect(self._open)
        self.btn_review = QPushButton("  Analyser"); self.btn_review.setObjectName("primary")
        self.btn_review.setIcon(icon("scan", "white"))
        self.btn_review.setEnabled(False); self.btn_review.clicked.connect(self.analyze)
        self.btn_zone = QPushButton("  Zone manuelle"); self.btn_zone.setObjectName("navTool")
        self.btn_zone.setCheckable(True); self.btn_zone.setIcon(icon("scan", "white"))
        self.btn_zone.toggled.connect(self._toggle_zone)
        self.btn_redact = QPushButton("  Caviarder (PDF)"); self.btn_redact.setObjectName("info")
        self.btn_redact.setIcon(icon("shield", "white")); self.btn_redact.clicked.connect(self._redact_clicked)
        self.btn_text = QPushButton("  Extraire en .txt"); self.btn_text.setObjectName("navTool")
        self.btn_text.setIcon(icon("document", "white")); self.btn_text.clicked.connect(self._text_clicked)
        for b in (self.btn_open, self.btn_review, self.btn_zone,
                  self.btn_redact, self.btn_text):
            bar.addWidget(b)
        action_band = QFrame(); action_band.setObjectName("ActionBand")
        action_band.setLayout(bar)
        band_row = QHBoxLayout(); band_row.setContentsMargins(18, 0, 18, 0)
        band_row.addWidget(action_band)
        root.addLayout(band_row)

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

        body = QHBoxLayout(); body.setContentsMargins(18, 12, 18, 8); body.setSpacing(12)
        body.addWidget(canvas_card, 3); body.addWidget(ent_card, 2)
        root.addLayout(body, 1)

        # ---- pagination + zoom ----
        self.pager = QHBoxLayout(); self.pager.setContentsMargins(18, 6, 18, 14)
        # zoom (gauche) : − / % (remise à 100 %) / +
        self.btn_zoom_out = QPushButton("−"); self.btn_zoom_out.setObjectName("pager")
        self.btn_zoom_out.setToolTip("Dézoomer (Ctrl + molette)")
        self.btn_zoom_out.clicked.connect(lambda: self._zoom(self.canvas.zoom_out))
        self.lbl_zoom = QPushButton("100 %"); self.lbl_zoom.setObjectName("pager")
        self.lbl_zoom.setToolTip("Réinitialiser le zoom")
        self.lbl_zoom.clicked.connect(lambda: self._zoom(self.canvas.reset_zoom))
        self.btn_zoom_in = QPushButton("+"); self.btn_zoom_in.setObjectName("pager")
        self.btn_zoom_in.setToolTip("Zoomer (Ctrl +, ou Ctrl + molette)")
        self.btn_zoom_in.clicked.connect(lambda: self._zoom(self.canvas.zoom_in))
        self.btn_fit = QPushButton("Ajuster"); self.btn_fit.setObjectName("pager")
        self.btn_fit.setToolTip("Ajuster à la largeur (Ctrl + 9)")
        self.btn_fit.clicked.connect(lambda: self._zoom(self.canvas.fit_to_width))
        self.lbl_shortcuts = QLabel(
            "Ctrl +/− : zoom · Ctrl 0 : 100 % · Ctrl 9 : ajuster · Ctrl + molette")
        self.lbl_shortcuts.setObjectName("hint")
        # pagination (droite)
        self.btn_prev = QPushButton("‹ Précédent"); self.btn_prev.setObjectName("pager")
        self.btn_prev.clicked.connect(lambda: self._go(self.page - 1))
        self.lbl_page = QLabel(""); self.lbl_page.setObjectName("pageInfo")
        self.lbl_page.setAlignment(Qt.AlignCenter)
        self.btn_next = QPushButton("Suivant ›"); self.btn_next.setObjectName("pager")
        self.btn_next.clicked.connect(lambda: self._go(self.page + 1))
        self.pager.addWidget(self.btn_zoom_out); self.pager.addWidget(self.lbl_zoom)
        self.pager.addWidget(self.btn_zoom_in); self.pager.addWidget(self.btn_fit)
        self.pager.addSpacing(14); self.pager.addWidget(self.lbl_shortcuts)
        self.pager.addStretch()
        self.pager.addWidget(self.btn_prev)
        self.pager.addWidget(self.lbl_page)
        self.pager.addWidget(self.btn_next)
        self.pager_widget = QWidget(); self.pager_widget.setObjectName("PagerBar")
        self.pager_widget.setLayout(self.pager); self.pager_widget.hide()
        root.addWidget(self.pager_widget)

        # ---- raccourcis clavier de zoom (documentés via lbl_shortcuts) ----
        self._make_zoom_shortcuts()

        # Voile "travail en cours" superposé (masqué par défaut)
        self._overlay = QLabel("⏳  Analyse en cours…", self)
        self._overlay.setObjectName("busyOverlay")
        self._overlay.setAlignment(Qt.AlignCenter)
        self._overlay.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._overlay.isVisible():
            self._overlay.setGeometry(self.rect())
        # en mode « Ajuster », le canvas se recale seul : on resynchronise le %.
        if self.canvas.has_page():
            self._update_zoom_label()

    def paintEvent(self, _event):
        paint_grid(self)

    # ---------- ouverture ----------
    def _open(self):
        path, _ = QFileDialog.getOpenFileName(self, "Ouvrir un PDF", "", "PDF (*.pdf)")
        if path:
            self.load_path(path)

    def load_path(self, path: str):
        self.path = Path(path)
        self.session = None
        self._png_cache = {}
        self._page_count = 0
        self.canvas.clear()
        self.side.hide(); self.pager_widget.hide()
        self.btn_zone.setChecked(False)
        is_pdf = self.path.suffix.lower() == ".pdf"
        self.btn_review.setEnabled(is_pdf)
        self.name_label.setText(self.path.name)
        if not is_pdf:
            self.meta_label.setText("Fichier PDF — cliquez « Analyser »")
            return
        # Aperçu immédiat (non caviardé, sans modèle) : confirme que le PDF est
        # lisible et lève tout de suite corrompu/chiffré via un message explicite.
        try:
            self._page_count = pdf_io.page_count(self.path)
            self.page = 0
            self._render_page()
            self._show_pager()
            self.meta_label.setText(
                f"{self._page_count} page(s) — cliquez « Analyser » pour détecter")
        except (CorruptPdfError, EncryptedPdfError) as e:
            self.meta_label.setText("PDF non exploitable")
            QMessageBox.warning(self, "PDF non exploitable", str(e))

    # ---------- analyse ----------
    def analyze(self):
        if self._worker and self._worker.isRunning():
            return
        if not self.path:
            return
        self._degraded = not (self.loader.has_detector() or is_model_available())
        # Le détecteur est construit DANS le worker (pas ici, sur le thread UI) :
        # une construction lente affiche l'overlay, un échec remonte via `error`.
        loader = ModelLoader(NullNer()) if self._degraded else self.loader
        self._set_busy(True)
        self._worker = PdfScanWorker(self.path, loader, self.ref)
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
        self._show_pager()
        self._render_page()

    # ---------- panneau latéral (même structure que FileScreen) ----------
    def _build_side(self):
        bold = QFont(); bold.setBold(True)
        self.side.blockSignals(True); self.side.clear()
        for t in self.session.types():
            top = QTreeWidgetItem([t, f"×{self.session.count_retained(t)}"])
            top.setForeground(0, QColor(color_for(t)))
            top.setForeground(1, QColor(color("text_muted")))
            top.setTextAlignment(1, Qt.AlignRight | Qt.AlignVCenter)
            top.setFont(0, bold)
            top.setData(0, Qt.UserRole, ("type", t, None))
            top.setFlags(top.flags() | Qt.ItemIsUserCheckable)
            top.setCheckState(0, Qt.Checked if self.session.is_type_enabled(t) else Qt.Unchecked)
            for value, n in self.session.values_for(t):
                confirmed = self.session.is_value_confirmed(t, value)
                label = value if confirmed else f"{value}   ⚠ clé non conforme"
                child = QTreeWidgetItem([label, f"×{n}"])
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
        if self.path is None or self._page_count == 0:
            return
        self.canvas.set_page(self._png_for(self.page), RENDER_ZOOM)
        # Avant analyse (session absente) : aperçu sans overlays.
        if self.session is not None:
            self.canvas.set_overlays(self.session.retained_entity_rects(self.page),
                                     self.session.manual_rects(self.page),
                                     self.session.unconfirmed_entity_rects(self.page))
        else:
            self.canvas.set_overlays([], [])
        self.lbl_page.setText(f"Page {self.page + 1} / {self._page_count}")
        self.btn_prev.setEnabled(self.page > 0)
        self.btn_next.setEnabled(self.page < self._page_count - 1)

    def _go(self, page: int):
        self.page = max(0, min(page, self._page_count - 1))
        self._render_page()

    # ---------- zoom ----------
    def _make_zoom_shortcuts(self):
        # Ctrl + / Ctrl = (même touche sans Maj) → zoom ; Ctrl - → dézoom ;
        # Ctrl 0 → 100 % ; Ctrl 9 → ajuster à la largeur.
        specs = [
            ("Ctrl++", self.canvas.zoom_in), ("Ctrl+=", self.canvas.zoom_in),
            ("Ctrl+-", self.canvas.zoom_out),
            ("Ctrl+0", self.canvas.reset_zoom),
            ("Ctrl+9", self.canvas.fit_to_width),
        ]
        for seq, action in specs:
            sc = QShortcut(QKeySequence(seq), self)
            sc.activated.connect(lambda a=action: self._zoom(a))

    def _zoom(self, action):
        action()
        self._update_zoom_label()

    def _update_zoom_label(self):
        self.lbl_zoom.setText(f"{round(self.canvas.display_zoom * 100)} %")

    def _show_pager(self):
        """Affiche la barre du bas dès qu'une page est présente. Les contrôles
        de pagination ne sont visibles qu'en multi-page ; le zoom reste toujours
        disponible."""
        multi = self._page_count > 1
        for w in (self.btn_prev, self.lbl_page, self.btn_next):
            w.setVisible(multi)
        self.pager_widget.setVisible(self._page_count >= 1)
        self._update_zoom_label()

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
        # Après analyse, on masque l'ensemble retenu de la session (décochages
        # de la revue honorés) — cohérent avec le mode caviardage. Sans session
        # (extraction directe sans « Analyser »), on re-détecte tout.
        if self.session is not None:
            return pdf_io.anonymize_pdf_text_from_session(
                self.path, self.session, out_dir, when)
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
        # Les zones manuelles n'ont pas de correspondance dans le texte plat :
        # elles ne sont caviardées que dans le PDF. On prévient l'utilisateur
        # avant l'export .txt pour éviter la surprise (fuite d'un tampon/signature).
        if self.session is not None and self.session.has_manual_rects():
            confirm = QMessageBox.question(
                self, "Zones manuelles ignorées",
                "Les zones tracées manuellement ne seront pas incluses dans le "
                ".txt : elles n'existent que pour le caviardage du PDF.\n\n"
                "Pour masquer un tampon ou une signature, utilisez « Caviarder "
                "(PDF) ».\n\nContinuer l'export en .txt ?")
            if confirm != QMessageBox.Yes:
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
