# anonymator/ui/image_screen.py
"""Écran de revue d'une image.

L'OCR PROPOSE des zones, l'utilisateur VALIDE et complète à la souris. La revue
est obligatoire : aucun chemin ne mène à un fichier de sortie sans être passé
par elle (`run_redact` rend None tant qu'il n'y a pas de session).

Une image n'a qu'une page : pas de pagination. Et pas de mode « extraire en
.txt » — hors périmètre de ce lot."""
from datetime import datetime
from io import BytesIO
from pathlib import Path

from PySide6.QtWidgets import (QWidget, QFrame, QVBoxLayout, QHBoxLayout,
                               QPushButton, QLabel, QFileDialog, QMessageBox,
                               QTreeWidget, QTreeWidgetItem, QHeaderView)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont

from anonymator.core.model_status import is_model_available
from anonymator.core.spatial_review_session import SpatialReviewSession
from anonymator.files.image import image_io
from anonymator.files.image.ocr import NullOcr
from anonymator.ner import NullNer
from anonymator.ui.components.banner import ModelBanner
from anonymator.ui.components.cards import Card
from anonymator.ui.components.grid import paint_grid
from anonymator.ui.components.header import HeaderBand
from anonymator.ui.components.nav_band import NavBand
from anonymator.ui.colors import color_for
from anonymator.ui.components.perimetre_card import PerimetreCard
from anonymator.ui.icons import icon
from anonymator.ui.image_scan_worker import ImageScanWorker
from anonymator.ui.model_loader import ModelLoader
from anonymator.ui.spatial_canvas import SpatialCanvas
from anonymator.ui.theme import color

_FILTRE = "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp)"

# Une image est déjà en pixels : contrairement à une page PDF rendue à 2x, le
# facteur entre coordonnées de scène et coordonnées source vaut 1.
_ZOOM_SOURCE = 1.0


class ImageScreen(QWidget):
    def __init__(self, ref, loader, prefs, on_back, on_request_model=None):
        super().__init__()
        self.setObjectName("ImageBg")
        self.setStyleSheet(f"#ImageBg {{ background: {color('grid_bg')}; }}")
        self.ref, self.loader, self.prefs = ref, loader, prefs
        self.on_request_model = on_request_model
        self.path: Path | None = None
        self.session: SpatialReviewSession | None = None
        self._busy = False
        self._degraded = False
        self._worker: ImageScanWorker | None = None
        # Fournisseur de moteur OCR, appelé DANS le worker : construire
        # RapidOcrEngine charge 32 Mo, l'écran doit rester instantané à
        # l'ouverture. Remplacé par main_window, et par FakeOcr en test.
        self.ocr_provider = NullOcr

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(HeaderBand())
        root.addWidget(NavBand("Image", "scan", on_home=on_back))
        root.addSpacing(14)
        self.banner = ModelBanner(on_install=self._request_model)
        root.addWidget(self.banner)

        # ---- barre d'action ----
        bar = QHBoxLayout()
        bar.setContentsMargins(18, 14, 18, 8)
        bar.setSpacing(12)
        self._file_ic = QLabel()
        self._file_ic.setPixmap(icon("document", color("action")).pixmap(22, 22))
        info_col = QVBoxLayout()
        info_col.setSpacing(1)
        self.name_label = QLabel("Aucune image")
        self.name_label.setObjectName("fileName")
        self.meta_label = QLabel("Importez une capture d'écran, un scan ou une photo")
        self.meta_label.setObjectName("fileMeta")
        info_col.addWidget(self.name_label)
        info_col.addWidget(self.meta_label)
        bar.addWidget(self._file_ic)
        bar.addLayout(info_col)
        bar.addStretch()

        self.btn_open = QPushButton("  Ouvrir")
        self.btn_open.setObjectName("navOpen")
        self.btn_open.setIcon(icon("folder", "white"))
        self.btn_open.clicked.connect(self._open)
        self.btn_review = QPushButton("  Analyser")
        self.btn_review.setObjectName("primary")
        self.btn_review.setIcon(icon("scan", "white"))
        self.btn_review.setEnabled(False)
        self.btn_review.clicked.connect(self.analyze)
        self.btn_zone = QPushButton("  Zone manuelle")
        self.btn_zone.setObjectName("navTool")
        self.btn_zone.setCheckable(True)
        self.btn_zone.setIcon(icon("scan", "white"))
        self.btn_zone.toggled.connect(self._toggle_zone)
        self.btn_redact = QPushButton("  Caviarder et enregistrer")
        self.btn_redact.setObjectName("info")
        self.btn_redact.setIcon(icon("shield", "white"))
        self.btn_redact.clicked.connect(self._redact_clicked)
        for b in (self.btn_open, self.btn_review, self.btn_zone, self.btn_redact):
            bar.addWidget(b)
        action_band = QFrame()
        action_band.setObjectName("ActionBand")
        action_band.setLayout(bar)
        band_row = QHBoxLayout()
        band_row.setContentsMargins(18, 0, 18, 0)
        band_row.addWidget(action_band)
        root.addLayout(band_row)

        # ---- corps : canevas (gauche) + entités et périmètre (droite) ----
        self.canvas = SpatialCanvas()
        self.canvas.manual_rect_drawn.connect(self._on_manual_rect)
        canvas_card = Card("document", "Aperçu de l'image")
        canvas_card.body.addWidget(self.canvas)

        self.side = QTreeWidget()
        self.side.setHeaderHidden(True)
        self.side.setColumnCount(2)
        self.side.setRootIsDecorated(True)
        self.side.header().setStretchLastSection(False)
        self.side.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.side.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.side.itemChanged.connect(self._on_side_changed)
        ent_card = Card("shield", "Zones proposées")
        hint = QLabel(
            "La reconnaissance de caractères n'est pas infaillible, surtout sur "
            "une photo. Relisez l'image : pour tout ce qu'elle a manqué, "
            "cliquez « Zone manuelle » et tracez un rectangle.")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        ent_card.body.addWidget(hint)
        ent_card.body.addWidget(self.side)
        self.side.hide()
        self.perimetre = PerimetreCard("image")
        ent_card.body.addWidget(self.perimetre)

        body = QHBoxLayout()
        body.setContentsMargins(18, 12, 18, 8)
        body.setSpacing(12)
        body.addWidget(canvas_card, 3)
        body.addWidget(ent_card, 2)
        root.addLayout(body, 1)

        # Voile « travail en cours » superposé (masqué par défaut). L'analyse
        # d'une photo prend plusieurs secondes : sans retour visuel,
        # l'utilisateur croit l'application figée.
        self._overlay = QLabel("⏳  Analyse de l'image en cours…", self)
        self._overlay.setObjectName("busyOverlay")
        self._overlay.setAlignment(Qt.AlignCenter)
        self._overlay.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._overlay.isVisible():
            self._overlay.setGeometry(self.rect())

    def paintEvent(self, _event):
        paint_grid(self)

    # ---------- ouverture ----------
    def _open(self):
        path, _ = QFileDialog.getOpenFileName(self, "Ouvrir une image", "", _FILTRE)
        if path:
            self.load_path(path)

    def load_path(self, path: str) -> None:
        self.path = Path(path)
        self.session = None
        self.side.clear()
        self.side.hide()
        self.canvas.clear()
        self.btn_zone.setChecked(False)
        self.btn_review.setEnabled(False)
        self.name_label.setText(self.path.name)
        # Aperçu immédiat, sans modèle : confirme que l'image est lisible et
        # lève tout de suite format non supporté / fichier corrompu.
        try:
            img = image_io.load_image(self.path)
        except (image_io.UnsupportedImageFormat,
                image_io.CorruptImageError) as exc:
            self.meta_label.setText(str(exc))
            return
        buf = BytesIO()
        img.save(buf, format="PNG")
        self.canvas.set_page(buf.getvalue(), _ZOOM_SOURCE)
        self.btn_review.setEnabled(True)
        self.meta_label.setText(
            f"{img.width} × {img.height} pixels — cliquez « Analyser »")

    # ---------- analyse ----------
    def analyze(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            return
        if self.path is None:
            return
        self._degraded = not (self.loader.has_detector() or is_model_available())
        loader = ModelLoader(NullNer()) if self._degraded else self.loader
        self._set_busy(True)
        self._worker = ImageScanWorker(self.path, self.ocr_provider, loader,
                                       self.ref)
        self._worker.scan_finished.connect(self._on_scanned)
        self._worker.error.connect(self._on_scan_error)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.start()

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        for b in (self.btn_open, self.btn_review, self.btn_redact):
            b.setEnabled(not busy)
        if busy:
            self._overlay.setGeometry(self.rect())
            self._overlay.raise_()
            self._overlay.show()
            self.setCursor(Qt.BusyCursor)
        else:
            self._overlay.hide()
            self.setCursor(Qt.ArrowCursor)

    def _on_scan_error(self, msg: str) -> None:
        self._set_busy(False)
        self.meta_label.setText(msg)

    def _on_scanned(self, pages) -> None:
        self._set_busy(False)
        self.session = SpatialReviewSession(pages, self.ref)
        self._build_side()
        self._refresh_overlays()
        total = self.session.total_occurrences()
        self.meta_label.setText(
            f"{total} zone(s) proposée(s) — vérifiez, décochez, et complétez "
            f"à la souris ce qui a été manqué.")

    # ---------- panneau latéral ----------
    def _build_side(self) -> None:
        """Miroir exact de `PdfScreen._build_side`.

        Les valeurs à clé de contrôle fausse portent la même mention que dans
        l'écran PDF et le mode Fichier, et restent décochées. Ce comportement
        est déjà le plus déroutant de l'outil : il ne doit pas en plus changer
        d'un format à l'autre."""
        gras = QFont()
        gras.setBold(True)
        self.side.blockSignals(True)
        self.side.clear()
        for etype in self.session.types():
            parent = QTreeWidgetItem(
                [etype, f"×{self.session.count_retained(etype)}"])
            parent.setForeground(0, QColor(color_for(etype)))
            parent.setForeground(1, QColor(color("text_muted")))
            parent.setTextAlignment(1, Qt.AlignRight | Qt.AlignVCenter)
            parent.setFont(0, gras)
            parent.setData(0, Qt.UserRole, ("type", etype, None))
            parent.setFlags(parent.flags() | Qt.ItemIsUserCheckable)
            parent.setCheckState(
                0, Qt.Checked if self.session.is_type_enabled(etype)
                else Qt.Unchecked)
            for value, count in self.session.values_for(etype):
                confirme = self.session.is_value_confirmed(etype, value)
                libelle = value if confirme else f"{value}   ⚠ clé non conforme"
                child = QTreeWidgetItem([libelle, f"×{count}"])
                child.setForeground(1, QColor(color("text_muted")))
                child.setTextAlignment(1, Qt.AlignRight | Qt.AlignVCenter)
                # La valeur brute vit dans UserRole : le libellé est décoré,
                # elle ne l'est pas. Sans cela, cocher une valeur signalée
                # ne retrouverait aucune entité.
                child.setData(0, Qt.UserRole, ("value", etype, value))
                child.setFlags(child.flags() | Qt.ItemIsUserCheckable)
                child.setCheckState(
                    0, Qt.Checked
                    if self.session.is_value_enabled(etype, value)
                    else Qt.Unchecked)
                parent.addChild(child)
            self.side.addTopLevelItem(parent)
        self.side.expandAll()
        self.side.blockSignals(False)
        self.side.setVisible(bool(self.session.types()))

    def _on_side_changed(self, item, _col) -> None:
        if self.session is None:
            return
        kind, etype, value = item.data(0, Qt.UserRole)
        checked = item.checkState(0) == Qt.Checked
        if kind == "type":
            self.session.set_type_enabled(etype, checked)
        else:
            self.session.set_value_enabled(etype, value, checked)
        self._refresh_counts()
        self._refresh_overlays()

    def _refresh_counts(self) -> None:
        for i in range(self.side.topLevelItemCount()):
            parent = self.side.topLevelItem(i)
            _, etype, _ = parent.data(0, Qt.UserRole)
            parent.setText(1, f"×{self.session.count_retained(etype)}")

    def _refresh_overlays(self) -> None:
        if self.session is None:
            return
        # Ordre imposé par SpatialCanvas : entités, zones manuelles, puis les
        # non confirmées. Les intervertir n'échoue pas — ça affiche seulement
        # le mauvais style.
        self.canvas.set_overlays(
            self.session.retained_entity_rects(0),
            self.session.manual_rects(0),
            self.session.unconfirmed_entity_rects(0))

    # ---------- zones manuelles ----------
    def _toggle_zone(self, on: bool) -> None:
        self.canvas.set_draw_mode(on)

    def _on_manual_rect(self, rect: tuple) -> None:
        if self.session is None:
            return
        self.session.add_manual_rect(0, rect)
        self._refresh_overlays()

    # ---------- enregistrement ----------
    def run_redact(self, output_dir=None,
                   when: datetime | None = None) -> Path | None:
        """Rend None tant qu'aucune analyse n'a eu lieu : la revue est
        obligatoire avant toute destruction."""
        if self.session is None or self.path is None:
            return None
        out_dir = Path(output_dir) if output_dir else self._default_output_dir()
        rects = self.session.retained_rects_by_page().get(0, [])
        return image_io.anonymize_image_redact(
            self.path, rects, out_dir, when or datetime.now())

    def _default_output_dir(self) -> Path:
        configured = getattr(self.prefs, "output_dir", "") or ""
        return Path(configured) if configured else self.path.parent

    def _redact_clicked(self) -> None:
        if self.session is None:
            QMessageBox.information(
                self, "Analyse requise",
                "Cliquez « Analyser » avant d'enregistrer : la revue des zones "
                "est obligatoire.")
            return
        out = self.run_redact()
        self.meta_label.setText(f"Enregistré : {out}")
        QMessageBox.information(
            self, "Image caviardée",
            f"Image enregistrée :\n{out}\n\n"
            "Les pixels des zones retenues sont détruits et les métadonnées "
            "EXIF supprimées. L'original n'a pas été modifié.")

    # ---------- modèle ----------
    def _request_model(self) -> None:
        if self.on_request_model is not None:
            self.on_request_model()

    def hide_degraded(self) -> None:
        self.banner.hide()
