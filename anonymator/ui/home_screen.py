from pathlib import Path
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton
from PySide6.QtGui import QPainter, QPen, QColor, QPixmap
from PySide6.QtCore import Qt
from anonymator.ui.components.cards import NavCard

_HERO_BG = "#E8F3EA"
_GRID = "#E1EBE3"
_LOGO = Path(__file__).parent / "assets" / "logo.png"


class HeroPanel(QWidget):
    """Panneau gauche : fond vert pâle + grille de cadrage légère."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Hero")
        self.setStyleSheet(f"#Hero {{ background: {_HERO_BG}; }}")

    def paintEvent(self, _event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(_HERO_BG))
        pen = QPen(QColor(_GRID)); pen.setWidth(1)
        p.setPen(pen)
        step = 26
        w, h = self.width(), self.height()
        x = step
        while x < w:
            p.drawLine(x, 0, x, h); x += step
        y = step
        while y < h:
            p.drawLine(0, y, w, y); y += step
        p.end()


class HomeScreen(QWidget):
    def __init__(self, on_text, on_file, on_settings,
                 model_available: bool = True, on_download=None, on_dismiss=None,
                 on_pdf=None, on_rules=None, on_about=None):
        super().__init__()
        self._on_dismiss = on_dismiss
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        hero = HeroPanel()
        hv = QVBoxLayout(hero)
        hv.setContentsMargins(48, 44, 48, 44)
        has_logo = _LOGO.exists()
        if has_logo:
            logo = QLabel()
            logo.setPixmap(QPixmap(str(_LOGO)).scaledToWidth(250, Qt.SmoothTransformation))
        else:
            logo = QLabel("CUMA"); logo.setObjectName("title")
            logo.setStyleSheet("color: #31B700; font-size: 34px; font-weight: 800;")
        title = QLabel("Anonymisez.\nPartagez l'essentiel.")
        title.setObjectName("title")
        sub = QLabel("Protégez noms, adresses et coordonnées avant tout partage. "
                     "Traitement 100% local, aucune donnée envoyée.")
        sub.setObjectName("muted"); sub.setWordWrap(True)
        sub.setStyleSheet("color:#6B7C72; font-size:16px; line-height:140%;")
        hv.addWidget(logo); hv.addSpacing(120); hv.addWidget(title); hv.addWidget(sub)
        hv.addStretch()
        # tagline déjà présente dans le logo officiel → on ne la répète qu'en repli texte
        if not has_logo:
            foot = QLabel("la puissance du <span style='color:#E8621A;font-weight:700'>groupe</span>")
            foot.setTextFormat(Qt.RichText)
            hv.addWidget(foot)

        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(40, 60, 40, 40)
        self.model_card = QWidget(); self.model_card.setObjectName("modelInvite")
        mc = QVBoxLayout(self.model_card); mc.setContentsMargins(16, 14, 16, 14); mc.setSpacing(8)
        mc_title = QLabel("🧠  Activer la détection intelligente")
        mc_title.setStyleSheet("font-weight: 700; font-size: 15px;")
        mc_desc = QLabel("Noms, adresses et organisations — téléchargement unique (~300 Mo). "
                         "Les détections par règles (IBAN, e-mail, téléphone…) fonctionnent déjà sans elle.")
        mc_desc.setWordWrap(True); mc_desc.setObjectName("muted")
        mc_btns = QHBoxLayout()
        self.btn_model_download = QPushButton("Télécharger maintenant")
        self.btn_model_download.setObjectName("primary")
        if on_download is not None:
            self.btn_model_download.clicked.connect(on_download)
        self.btn_model_later = QPushButton("Plus tard"); self.btn_model_later.setObjectName("ghost")
        self.btn_model_later.clicked.connect(self._dismiss)
        mc_btns.addWidget(self.btn_model_download); mc_btns.addWidget(self.btn_model_later); mc_btns.addStretch()
        mc.addWidget(mc_title); mc.addWidget(mc_desc); mc.addLayout(mc_btns)
        self.model_card.setStyleSheet(
            "#modelInvite { background: rgba(0, 150, 94, 0.08); "
            "border: 1px solid rgba(0, 150, 94, 0.45); border-radius: 10px; }")
        self.model_card.setVisible(not model_available)
        rv.addWidget(self.model_card); rv.addSpacing(12)
        label = QLabel("PAR OÙ COMMENCER ?"); label.setObjectName("sectionLabel")
        rv.addWidget(label); rv.addSpacing(12)
        self.btn_text = NavCard("document", "Coller du texte",
                                "Analyser et masquer un texte collé", on_click=on_text)
        self.btn_file = NavCard("folder", "Importer un fichier",
                                ".txt, .csv ou .xlsx", on_click=on_file)
        self.btn_pdf = NavCard("document", "Importer un PDF",
                               "Caviarder ou extraire (PDF natifs)", on_click=on_pdf)
        self.btn_settings = NavCard("settings", "Paramètres",
                                    "Thème, dossier, types, modèle", on_click=on_settings)
        self.btn_rules = NavCard("shield", "Gestion des règles",
                                 "Règles métier", on_click=on_rules)
        self.btn_about = NavCard("sparkle", "À propos",
                                 "Licence, version et mentions", on_click=on_about)
        for c in (self.btn_text, self.btn_file, self.btn_pdf,
                  self.btn_settings, self.btn_rules, self.btn_about):
            rv.addWidget(c)
        rv.addStretch()

        root.addWidget(hero, 5)
        root.addWidget(right, 6)

    def _dismiss(self):
        self.model_card.setVisible(False)
        if self._on_dismiss is not None:
            self._on_dismiss()

    def set_model_available(self, available: bool):
        self.model_card.setVisible(not available)
