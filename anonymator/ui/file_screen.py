import csv
from datetime import datetime
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QFrame, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QTableWidget, QTableWidgetItem, QFileDialog,
                               QMessageBox, QTreeWidget, QTreeWidgetItem, QLineEdit,
                               QCheckBox, QMenu, QComboBox)
from PySide6.QtGui import QColor, QCursor
from PySide6.QtCore import Qt
from anonymator.ui.components.grid import paint_grid
from anonymator.ui.theme import color
from anonymator.files.anonymize_file import (anonymize_file, UnsupportedFormat, FileResult)
from anonymator.files import csv_io
from anonymator.output_naming import anonymized_path
from anonymator.files.anonymize_file import csv_column_plans
from anonymator.files.columns import classify_columns
from anonymator.core.file_review_session import FileReviewSession
from anonymator.core.tabular_review_session import AUTO, CLEAR, MASK
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
from anonymator.core.ooxml_review_session import OoxmlReviewSession
from anonymator.core.xlsx_review_session import XlsxReviewSession
from anonymator.ui.ooxml_scan_worker import OoxmlScanWorker
from anonymator.ui.xlsx_scan_worker import XlsxScanWorker
from anonymator.ui.components.perimetre_card import PerimetreCard
from anonymator.files.ooxml import xml_parts

PAGE_SIZE = 20

# Marqueur d'un arbitrage manuel dans l'intitulé de colonne : l'en-tête doit
# dire d'un coup d'œil que le plan automatique a été recouvert.
_OVERRIDE_MARK = {MASK: "🔒 ", CLEAR: "🔓 "}


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
        self._ooxml = None
        self._xlsx = None            # XlsxScanResult de la revue en cours
        self._sheet: str | None = None
        self._sheet_to_restore: str | None = None
        self._sheet_headers: dict[str, bool] = {}   # choix explicites par feuille
        # Forme de l'aperçu : "grid" (CSV, classeur) ou "units" (docx/pptx).
        # Remplace un test sur la classe de la session : à trois sessions, un
        # troisième `elif isinstance(...)` serait la faute.
        self._view = "grid"
        self.page = 0
        self._busy = False
        self._degraded = False
        self._worker: FileScanWorker | None = None
        self._anon_worker: FileAnonymizeWorker | None = None
        self._pending_choices: dict | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)
        root.addWidget(HeaderBand())
        root.addWidget(NavBand("Fichier", "folder", on_home=on_back))
        root.addSpacing(14)   # laisse respirer le fond quadrillé au-dessus de la barre

        self.banner = ModelBanner(on_install=self._request_model)
        root.addWidget(self.banner)

        # ---- barre d'action : infos fichier (gauche) + actions (droite) ----
        bar = QHBoxLayout(); bar.setContentsMargins(18, 14, 18, 8); bar.setSpacing(12)
        self._file_ic = QLabel(); self._file_ic.setPixmap(icon("document", color("action")).pixmap(22, 22))
        info_col = QVBoxLayout(); info_col.setSpacing(1)
        self.name_label = QLabel("Aucun fichier"); self.name_label.setObjectName("fileName")
        self.meta_label = QLabel("Importez un fichier .txt, .csv, .xlsx, .docx ou .pptx")
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
        band_row = QHBoxLayout(); band_row.setContentsMargins(18, 0, 18, 0)
        band_row.addWidget(action_band)
        root.addLayout(band_row)

        # ---- corps : extrait (gauche) + entités (droite) ----
        self.table = QTableWidget()
        self.table.setShowGrid(True)
        self.table.setAlternatingRowColors(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setDefaultAlignment(Qt.AlignCenter)
        head = self.table.horizontalHeader()
        head.setSectionsClickable(True)
        head.sectionClicked.connect(self._on_header_clicked)
        table_card = Card("document", "Écritures comptables — extrait")
        # La détection d'en-tête est une heuristique : sur un fichier sans
        # colonne numérique elle se trompe, et tout le typage par nom de
        # colonne tombe avec elle. L'utilisateur doit pouvoir trancher.
        self.header_switch = QCheckBox("Première ligne = en-têtes")
        self.header_switch.setObjectName("headerSwitch")
        self.header_switch.toggled.connect(self._on_header_toggled)
        self.header_switch.hide()
        # Une feuille à la fois : la lecture tabulaire est l'objet même de la
        # revue, et concaténer les feuilles la perdrait.
        self.sheet_box = QComboBox()
        self.sheet_box.setObjectName("sheetBox")
        self.sheet_box.currentTextChanged.connect(self._on_sheet_changed)
        self.sheet_box.hide()
        table_card.head.addWidget(self.sheet_box)
        table_card.head.addWidget(self.header_switch)
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

        # Bloc distinct sous les entités : périmètre du traitement. Affiché
        # pour les trois formats OOXML — le classeur en était privé, donc rien
        # n'y signalait ce qui échappait au traitement.
        self.perimetre_card = Card("eye", "Périmètre du traitement")
        self.perimetre = PerimetreCard()
        self.perimetre_card.body.addWidget(self.perimetre)
        self.perimetre_card.hide()

        right = QVBoxLayout(); right.setSpacing(12)
        right.addWidget(ent_card, 1)
        right.addWidget(self.perimetre_card)

        body = QHBoxLayout(); body.setContentsMargins(18, 12, 18, 8); body.setSpacing(12)
        body.addWidget(table_card, 3)
        body.addLayout(right, 2)
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
            self.meta_label.setText("Importez un fichier .txt, .csv, .xlsx, .docx ou .pptx")
            return
        self.name_label.setText(self.path.name)
        kind = f"Fichier {self.path.suffix.lstrip('.').upper()}"
        parts = [kind]
        if self.doc is not None:
            parts.append(f"{_fmt_int(len(self.doc.rows))} lignes")
        elif self._xlsx is not None:
            parts.append(f"{len(self._xlsx.sheets)} feuille(s)")
        if status is not None:
            parts.append(status)
        elif self.session is not None:
            parts.append(f"{_fmt_int(self.session.total_occurrences())} entités détectées")
        self.meta_label.setText(" · ".join(parts))

    # ---------- opening / preview ----------
    def _open(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Ouvrir", "",
            "Fichiers (*.txt *.csv *.xlsx *.docx *.pptx)")
        if path:
            self.load_path(path)

    def load_path(self, path: str):
        self.path = Path(path)
        self.doc = None
        self.session = None
        self._ooxml = None
        self._xlsx = None
        self._sheet = None
        self._sheet_to_restore = None
        self._sheet_headers = {}
        self._view = "grid"
        self._pending_choices = None   # arbitrages d'un autre fichier : sans objet
        self.side.hide(); self.pager_widget.hide()
        self.occ_badge.hide(); self._hint.hide()
        self.sheet_box.hide()
        suffix = self.path.suffix.lower()
        self.btn_review.setEnabled(
            suffix in (".csv", ".txt", ".xlsx", ".docx", ".pptx"))
        if suffix == ".csv":
            # Lecture immédiate (l'aperçu en dépend) : un fichier illisible ou
            # verrouillé doit se dire ici, en clair. Sans ce garde, l'exception
            # remontait au filet de sécurité de __main__ et s'affichait en
            # « Erreur inattendue », sans rapport avec ce que l'utilisateur venait
            # de faire.
            try:
                self.doc = csv_io.read_csv(self.path)
            except (OSError, UnicodeDecodeError, csv.Error) as exc:
                self._reject_file("Fichier illisible", str(exc))
                return
            self.header_switch.blockSignals(True)     # reflet, pas une action
            self.header_switch.setChecked(self.doc.has_header)
            self.header_switch.blockSignals(False)
            self.header_switch.show()
            self._fill_preview(self.doc.rows[:50])
        else:
            # Un classeur n'est pas lu ici : sa grille apparaît avec l'analyse,
            # qui le charge hors thread UI (cf. XlsxScanWorker).
            self.header_switch.hide()
            self.table.clear()
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
        self.perimetre_card.setVisible(False)
        self._set_meta()

    def _reject_file(self, title: str, detail: str) -> None:
        """Abandonne le fichier en cours et le dit. L'écran revient à son état
        « aucun fichier » : rien à analyser, rien à anonymiser."""
        self.path = None
        self.doc = None
        self.btn_review.setEnabled(False)
        self.header_switch.hide()
        self.table.clear(); self.table.setRowCount(0); self.table.setColumnCount(0)
        self._set_meta()
        QMessageBox.warning(self, title, detail)

    def _capture_choices(self) -> dict | None:
        """Arbitrages manuels de la revue en cours. Types et valeurs sont
        indexés par (type, valeur) : ils survivent à un changement de plan de
        colonnes. Les forçages de colonne, eux, sont positionnels par nature —
        et la position reste valide, car changer l'hypothèse d'en-tête déplace
        des lignes, pas des colonnes."""
        if self.session is None:
            return None
        types = {t: self.session.is_type_enabled(t) for t in self.session.types()}
        values = {(t, v): self.session.is_value_enabled(t, v)
                  for t in self.session.types()
                  for v, _n in self.session.values_for(t)}
        return {"types": types, "values": values,
                "columns": self.session.column_overrides()}

    def _restore_choices(self, choices: dict | None) -> None:
        """Réapplique les arbitrages qui gardent un sens dans la nouvelle
        analyse ; ignore en silence ce qui a disparu.

        Les colonnes d'abord : un forçage crée des entités, et les décochages
        de valeurs doivent pouvoir porter dessus."""
        if not choices or self.session is None:
            return
        for key, (mode, etype) in choices.get("columns", {}).items():
            if self.session.has_column(key):
                self.session.set_column_override(key, mode, etype)
        for etype, enabled in choices["types"].items():
            if etype in self.session.types():
                self.session.set_type_enabled(etype, enabled)
        known = {(t, v) for t in self.session.types()
                 for v, _n in self.session.values_for(t)}
        for (etype, value), enabled in choices["values"].items():
            if (etype, value) in known:
                self.session.set_value_enabled(etype, value, enabled)

    def _on_header_toggled(self, checked: bool):
        """L'hypothèse d'en-tête décide du typage des colonnes, donc du
        périmètre : une revue faite sous l'ancienne hypothèse ne peut pas être
        rejouée telle quelle. Elle représente du travail manuel, on demande
        avant de la relancer, et on reporte les arbitrages sur la suivante."""
        if self._xlsx is not None:
            self._on_sheet_header_toggled(checked)
            return
        if self.doc is None:
            return
        had_session = self.session is not None
        if had_session:
            if not self._confirm_reanalysis():
                self.header_switch.blockSignals(True)
                self.header_switch.setChecked(not checked)   # retour à l'état
                self.header_switch.blockSignals(False)
                return
            self._pending_choices = self._capture_choices()
        self.doc.has_header = checked
        self.session = None
        self.side.hide(); self._hint.hide(); self.occ_badge.hide()
        self.pager_widget.hide()
        self.page = 0
        self._fill_preview(self.doc.rows[:50])
        self._set_meta()
        if had_session:
            # La relance a été annoncée à l'utilisateur, et acceptée : elle doit
            # avoir lieu. Sans elle, la revue disparaissait sans être refaite, et
            # « Anonymiser & enregistrer » repartait en détection automatique —
            # une colonne forcée à la main n'était alors pas masquée du tout.
            self.analyze()

    def _confirm_reanalysis(self) -> bool:
        answer = QMessageBox.question(
            self, "Relancer l'analyse ?",
            "Changer l'hypothèse d'en-tête modifie le périmètre des "
            "colonnes : l'analyse doit être relancée.\n\n"
            "Vos choix (valeurs, catégories et colonnes forcées) seront "
            "reportés sur la nouvelle analyse.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        return answer == QMessageBox.Yes

    def _on_sheet_header_toggled(self, checked: bool):
        """Côté classeur, l'analyse repart tout de suite. Un CSV sait
        re-afficher son aperçu sans rescan — ses lignes sont déjà en mémoire ;
        une feuille, elle, n'existe à l'écran que par le résultat du scan."""
        if self._sheet is None:
            return
        if self.session is not None and not self._confirm_reanalysis():
            self.header_switch.blockSignals(True)
            self.header_switch.setChecked(not checked)   # retour à l'état
            self.header_switch.blockSignals(False)
            return
        self._pending_choices = self._capture_choices()
        self._sheet_headers[self._sheet] = checked
        self._sheet_to_restore = self._sheet
        self.session = None
        self.analyze()

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

    def _header_override(self) -> bool | None:
        """Choix explicite de l'utilisateur, à substituer à la détection
        automatique. None hors CSV : la question ne se pose pas."""
        return None if self.doc is None else self.doc.has_header

    def run(self, when: datetime | None = None):
        if not self.path:
            return None
        out_dir = Path(self.prefs.output_dir) if self.prefs.output_dir else self.path.parent
        when = when or datetime.now()
        if self.session is not None:
            # Toutes les sessions savent s'appliquer et se rendre : l'écran n'a
            # pas à savoir de quel format il s'agit.
            out = anonymized_path(self.path, out_dir, when)
            report = self.session.apply_and_save(out)
            return FileResult(out, report)
        try:
            ner = self.loader.get()
            result = anonymize_file(self.path, ner, self.ref, out_dir, when,
                                    has_header=self._header_override())
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
            self.path, loader, self.ref, out_dir, datetime.now(),
            has_header=self._header_override())
        self._anon_worker.done.connect(self._on_anonymized)
        self._anon_worker.error.connect(self._on_run_error)
        self._anon_worker.finished.connect(self._anon_worker.deleteLater)
        self._anon_worker.finished.connect(self._forget_anon_worker)
        self._anon_worker.start()

    def _forget_worker(self):
        # Le worker a fini : son objet C++ est supprimé (deleteLater). On oublie
        # le wrapper (devenu mort) pour que le garde-fou de `analyze()` ne le
        # déréférence pas au prochain lancement. `sender()` évite d'effacer un
        # worker plus récent déjà assigné.
        if self.sender() is self._worker:
            self._worker = None

    def _forget_anon_worker(self):
        if self.sender() is self._anon_worker:
            self._anon_worker = None

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
        if self.path and self.path.suffix.lower() in (".docx", ".pptx"):
            self._degraded = not (self.loader.has_detector() or is_model_available())
            loader = ModelLoader(NullNer()) if self._degraded else self.loader
            self._set_busy(True)
            self._worker = OoxmlScanWorker(self.path, loader, self.ref)
            self._worker.scan_finished.connect(self._on_ooxml_scanned)
            self._worker.error.connect(self._on_scan_error)
            self._worker.finished.connect(self._worker.deleteLater)
            self._worker.finished.connect(self._forget_worker)
            self._worker.start()
            return
        if self.path and self.path.suffix.lower() == ".xlsx":
            self._degraded = not (self.loader.has_detector() or is_model_available())
            loader = ModelLoader(NullNer()) if self._degraded else self.loader
            self._set_busy(True)
            self._worker = XlsxScanWorker(self.path, loader, self.ref,
                                          self._sheet_headers)
            self._worker.scan_finished.connect(self._on_xlsx_scanned)
            self._worker.error.connect(self._on_scan_error)
            self._worker.finished.connect(self._worker.deleteLater)
            self._worker.finished.connect(self._forget_worker)
            self._worker.start()
            return
        if self.doc is None:
            return
        plans = csv_column_plans(self.doc)
        cols = set(plans)
        self._cols = cols
        # Plan complet, colonnes écartées comprises : c'est leur `reason` qui
        # explique à l'utilisateur pourquoi elles sont hors périmètre.
        self._full_plans = classify_columns(self.doc.rows, self.doc.has_header)
        self._degraded = not (self.loader.has_detector() or is_model_available())
        # Le détecteur est construit DANS le worker (pas ici, sur le thread UI) :
        # une construction lente affiche l'overlay, un échec remonte via `error`.
        loader = ModelLoader(NullNer()) if self._degraded else self.loader
        self._set_busy(True)
        self._worker = FileScanWorker(self.doc, loader, self.ref, plans)
        self._worker.scan_finished.connect(self._on_scanned)
        self._worker.error.connect(self._on_scan_error)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.finished.connect(self._forget_worker)
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
        self._view = "grid"
        self.session = FileReviewSession(self.doc, scanned, self.ref, self._cols,
                                         self._full_plans)
        self._restore_choices(self._pending_choices)
        self._pending_choices = None
        self._set_busy(False)
        self.banner.setVisible(self._degraded)
        self.occ_badge.setText(f"{_fmt_int(self.session.total_occurrences())} occ.")
        self.occ_badge.show(); self._hint.show()
        self.page = 0
        self._build_side()
        self.side.show(); self.pager_widget.show()
        self._render_page()

    def _on_xlsx_scanned(self, res):
        self._xlsx = res
        self._view = "grid"
        self.session = XlsxReviewSession(res, self.ref)
        self.sheet_box.blockSignals(True)
        self.sheet_box.clear()
        self.sheet_box.addItems(res.sheets)
        # Après une relance, on revient sur la feuille que l'utilisateur
        # regardait : le rescan est un moyen, pas une navigation.
        wanted = self._sheet_to_restore
        self._sheet = (wanted if wanted in res.sheets
                       else (res.sheets[0] if res.sheets else None))
        self._sheet_to_restore = None
        if self._sheet is not None:
            self.sheet_box.setCurrentText(self._sheet)
        self.sheet_box.blockSignals(False)
        self.sheet_box.show()
        self._restore_choices(self._pending_choices)
        self._pending_choices = None
        self._set_busy(False)
        self.banner.setVisible(self._degraded)
        self.occ_badge.setText(f"{_fmt_int(self.session.total_occurrences())} occ.")
        self.occ_badge.show(); self._hint.show()
        self.header_switch.blockSignals(True)        # reflet, pas une action
        self.header_switch.setChecked(self._grid_has_header())
        self.header_switch.blockSignals(False)
        self.header_switch.show()
        self.page = 0
        self._build_side()
        self.side.show(); self.pager_widget.show()
        self.perimetre.set_format("xlsx")
        self.perimetre_card.show()
        self._render_page()

    def _on_sheet_changed(self, title: str):
        if not title or self._xlsx is None:
            return
        self._sheet = title
        self.page = 0
        self.header_switch.blockSignals(True)
        self.header_switch.setChecked(self._grid_has_header())
        self.header_switch.blockSignals(False)
        self._render_page()

    def _on_ooxml_scanned(self, res):
        self._ooxml = res
        self._view = "units"
        if res.fmt == "docx":
            save_fn = lambda out: res.doc.save(str(out))
            post_fn = lambda out, rep: xml_parts.postprocess_docx(
                out, self._detector_for_apply(), self.ref, rep)
        else:
            save_fn = lambda out: res.doc.save(str(out))
            post_fn = lambda out, rep: xml_parts.postprocess_pptx(
                out, self._detector_for_apply(), self.ref, rep)
        self.session = OoxmlReviewSession(
            res.units, res.scanned, self.ref, save_fn, post_fn)
        self._set_busy(False)
        self.banner.setVisible(self._degraded)
        self.occ_badge.setText(f"{_fmt_int(self.session.total_occurrences())} occ.")
        self.occ_badge.show(); self._hint.show()
        self._build_side()
        self.perimetre.set_format(res.fmt)
        self.side.show(); self.perimetre_card.show()
        self.pager_widget.hide()
        self._render_units_page()

    def _detector_for_apply(self):
        # Post-passe (commentaires/notes) : même détecteur que l'analyse.
        return NullNer() if self._degraded else self.loader.get()

    def _render_units_page(self):
        units = self._ooxml.units
        self.table.clear()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Emplacement", "Texte extrait"])
        self.table.setRowCount(len(units))
        for r, u in enumerate(units):
            self.table.setItem(r, 0, QTableWidgetItem(u.location))
            item = QTableWidgetItem(u.text())
            ents = self.session.entities_for_unit(r)
            if ents:
                col = QColor(color_for(ents[0].type)); col.setAlpha(70)
                item.setBackground(col)
            else:
                pend = self.session.unconfirmed_for_unit(r)
                if pend:
                    col = QColor(color_for(pend[0].type)); col.setAlpha(28)
                    item.setBackground(col)
            self.table.setItem(r, 1, item)

    def _build_side(self):
        from PySide6.QtGui import QFont
        bold = QFont(); bold.setBold(True)
        ital = QFont(); ital.setItalic(True)
        self.side.blockSignals(True)
        self.side.clear()
        counts = self.session.counts_retained()
        for t in self.session.types():
            top = QTreeWidgetItem([t, f"×{counts.get(t, 0)}"])
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
                enabled = self.session.is_value_enabled(t, value)
                child.setCheckState(0, Qt.Checked if enabled else Qt.Unchecked)
                if not confirmed:
                    child.setFont(0, ital)
                    child.setForeground(0, QColor("#c47f17"))
                    child.setToolTip(
                        0, f"Reconnu comme {t} d'après son format, mais le contrôle "
                        "de la clé (checksum) a échoué : décoché par défaut, "
                        "cochez-le pour le masquer quand même.")
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
        self._render_current()

    def _render_current(self):
        if self._view == "units":
            self._render_units_page()
        else:
            self._render_page()

    def _refresh_counts(self):
        counts = self.session.counts_retained()      # une passe pour tous les types
        for i in range(self.side.topLevelItemCount()):
            top = self.side.topLevelItem(i)
            _, t, _ = top.data(0, Qt.UserRole)
            top.setText(1, f"×{counts.get(t, 0)}")

    def _data_rows(self):
        start = 1 if self._grid_has_header() else 0
        return list(range(start, len(self._grid_rows())))

    # ---------- grille courante (CSV ou feuille de classeur) ----------
    def _grid_rows(self) -> list[list[str]]:
        if self._xlsx is not None:
            return self._xlsx.matrices.get(self._sheet, [])
        return self.doc.rows if self.doc is not None else []

    def _grid_has_header(self) -> bool:
        if self._xlsx is not None:
            return bool(self._xlsx.has_header.get(self._sheet, False))
        return bool(self.doc is not None and self.doc.has_header)

    def _cell_entities(self, r: int, c: int):
        if self._xlsx is not None:
            return self.session.entities_for_cell(self._sheet, r, c)
        return self.session.entities_for_cell(r, c)

    def _cell_unconfirmed(self, r: int, c: int):
        if self._xlsx is not None:
            return self.session.unconfirmed_for_cell(self._sheet, r, c)
        return self.session.unconfirmed_for_cell(r, c)

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
        grid = self._grid_rows()
        rows = self._data_rows()
        width = max((len(r) for r in grid), default=0)
        page_rows = rows[self.page * PAGE_SIZE:(self.page + 1) * PAGE_SIZE]
        header = grid[0] if (grid and self._grid_has_header()) else None
        self.table.clear()
        self.table.setColumnCount(width)
        self.table.setRowCount(len(page_rows))
        # Les intitulés sont toujours posés : sans QTableWidgetItem d'en-tête,
        # il n'y a nulle part où accrocher l'infobulle ni le marqueur d'état.
        self.table.setHorizontalHeaderLabels(
            [header[c] if (header and c < len(header)) else f"col{c}"
             for c in range(width)])
        for vr, r in enumerate(page_rows):
            for c in range(width):
                val = grid[r][c] if c < len(grid[r]) else ""
                item = QTableWidgetItem(val)
                ents = self._cell_entities(r, c)
                if ents:
                    col = QColor(color_for(ents[0].type)); col.setAlpha(70)
                    item.setBackground(col)
                else:
                    # cellule sans entité retenue : signale les « non confirmées »
                    # (clé invalide) avec un fond atténué.
                    pend = self._cell_unconfirmed(r, c)
                    if pend:
                        col = QColor(color_for(pend[0].type)); col.setAlpha(28)
                        item.setBackground(col)
                self.table.setItem(vr, c, item)
        self._decorate_headers(width)
        last = self._page_count() - 1
        self.lbl_page.setText(f"Page {self.page + 1} / {self._page_count()}")
        self.btn_first.setEnabled(self.page > 0)
        self.btn_prev.setEnabled(self.page > 0)
        self.btn_next.setEnabled(self.page < last)
        self.btn_last.setEnabled(self.page < last)

    # ---------- arbitrage par colonne ----------
    def _column_key(self, col: int):
        """Clé de colonne pour la session : un index pour un CSV, un couple
        (feuille, index) pour un classeur — deux feuilles n'ont aucune raison
        de partager un plan."""
        return (self._sheet, col) if self._xlsx is not None else col

    def _header_label(self, col: int) -> str:
        rows = self._grid_rows()
        if self._grid_has_header() and rows and col < len(rows[0]):
            return rows[0][col]
        return f"col{col}"

    def _column_tooltip(self, key, mode: str, etype: str | None) -> str:
        reason = self.session.column_reason(key) or "colonne non classée"
        if mode == MASK:
            return (f"Colonne forcée : toutes les cellules non vides sont "
                    f"masquées en {self.ref.label_for(etype)}.\n"
                    f"Plan automatique : {reason}.")
        if mode == CLEAR:
            return (f"Colonne libérée : hors du périmètre.\n"
                    f"Plan automatique : {reason}.")
        return (f"Plan automatique : {reason}.\n"
                f"Cliquez l'en-tête pour forcer cette colonne.")

    def _decorate_headers(self, width: int):
        """Rend lisibles, sur l'en-tête, l'état de la colonne et sa raison."""
        if self.session is None:
            return
        for c in range(width):
            item = self.table.horizontalHeaderItem(c)
            if item is None:
                continue
            key = self._column_key(c)
            mode, etype = self.session.column_override(key)
            item.setText(_OVERRIDE_MARK.get(mode, "") + self._header_label(c))
            item.setToolTip(self._column_tooltip(key, mode, etype))

    def _build_column_menu(self, col: int):
        """Menu des trois états d'une colonne. Rendu séparément de son
        exécution : c'est ce qui le rend vérifiable sans piloter la souris."""
        key = self._column_key(col)
        mode, etype = self.session.column_override(key)
        menu = QMenu(self)
        actions = {}

        reason = self.session.column_reason(key) or "colonne non classée"
        auto = menu.addAction(f"Auto — {reason}")
        auto.setCheckable(True)
        auto.setChecked(mode == AUTO)
        actions[auto] = (AUTO, None)

        sub = menu.addMenu("Tout anonymiser")
        # Un forçage est une décision explicite : on propose tous les types,
        # y compris inactifs (le déduit d'abord), plus un masquage neutre pour
        # les colonnes sans type sémantique (nomenclatures).
        deduced = self.session.default_type_for(key)
        codes = self.ref.forceable_codes()
        if deduced in codes:
            codes = [deduced] + [c for c in codes if c != deduced]
        for code in codes:
            label = self.ref.label_for(code)
            if code == deduced:
                label += "   (déduit)"
            elif not self.ref.is_active(code):
                label += "   (inactif)"
            act = sub.addAction(label)
            act.setCheckable(True)
            act.setChecked(mode == MASK and etype == code)
            actions[act] = (MASK, code)
        sub.addSeparator()
        neutral = sub.addAction(
            f"{self.ref.label_for('MASK')} → {self.ref.tag_for('MASK')}")
        neutral.setCheckable(True)
        neutral.setChecked(mode == MASK and etype == "MASK")
        actions[neutral] = (MASK, "MASK")

        clear = menu.addAction("Tout libérer")
        clear.setCheckable(True)
        clear.setChecked(mode == CLEAR)
        actions[clear] = (CLEAR, None)
        return menu, actions

    def _on_header_clicked(self, col: int):
        if self.session is None or self._view != "grid":
            return
        menu, actions = self._build_column_menu(col)
        chosen = menu.exec(QCursor.pos())
        if chosen in actions:
            self.apply_column_override(col, *actions[chosen])

    def apply_column_override(self, col: int, mode: str,
                              etype: str | None = None):
        """Applique l'arbitrage et rafraîchit tout ce qu'il déplace : les
        entités d'une colonne forcée entrent dans l'arbre, donc le compteur
        d'occurrences et les cases à cocher bougent aussi."""
        self.session.set_column_override(self._column_key(col), mode, etype)
        self._build_side()
        self.occ_badge.setText(f"{_fmt_int(self.session.total_occurrences())} occ.")
        self._render_current()

    def _request_model(self):
        if self.on_request_model is not None:
            self.on_request_model()

    def hide_degraded(self):
        self._degraded = False
        self.banner.setVisible(False)
