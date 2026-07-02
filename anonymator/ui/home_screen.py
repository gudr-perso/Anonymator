from pathlib import Path
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton
from PySide6.QtGui import QPainter, QPen, QColor, QPixmap
from PySide6.QtCore import Qt
from anonymator.ui.components.cards import NavCard
from anonymator.ui.components.header import HeaderBand
from anonymator.ui.components.nav_band import NavBand
from anonymator.ui.theme import color

_ASSETS = Path(__file__).parent / "assets"


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


class HeroPanel(QWidget):
    """Panneau gauche : fond vert pâle + grille de cadrage légère."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Hero")
        self.setStyleSheet(f"#Hero {{ background: {color('grid_bg')}; }}")

    def paintEvent(self, _event):
        p = QPainter(self)
        bg, grid = color("grid_bg"), color("grid_line")
        p.fillRect(self.rect(), QColor(bg))
        pen = QPen(QColor(grid)); pen.setWidth(1)
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
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(HeaderBand())
        root.addWidget(NavBand("Accueil", "home", on_home=None))

        split_host = QWidget()
        split = QHBoxLayout(split_host)
        split.setContentsMargins(0, 0, 0, 0)
        split.setSpacing(0)

        hero = HeroPanel()
        hv = QVBoxLayout(hero)
        hv.setContentsMargins(48, 44, 48, 44)
        logo_path = _ASSETS / color("logo")
        has_logo = logo_path.exists()
        if has_logo:
            logo = QLabel()
            logo.setPixmap(QPixmap(str(logo_path)).scaledToWidth(250, Qt.SmoothTransformation))
        else:
            logo = QLabel("CUMA"); logo.setObjectName("title")
            logo.setStyleSheet(
                f"color: {color('primary')}; font-size: 34px; font-weight: 800;")
        title = QLabel("Anonymisez.\nPartagez l'essentiel.")
        title.setObjectName("title")
        title.setStyleSheet(f"color: {color('hero_text')};")
        sub = QLabel("Protégez noms, adresses et coordonnées avant tout partage. "
                     "Traitement 100% local, aucune donnée envoyée.")
        sub.setWordWrap(True)
        sub.setStyleSheet(
            f"color:{color('hero_muted')}; font-size:16px; line-height:140%;")
        hv.addWidget(logo); hv.addSpacing(120); hv.addWidget(title); hv.addWidget(sub)
        hv.addStretch()
        # tagline déjà présente dans le logo officiel → on ne la répète qu'en repli texte
        if not has_logo:
            foot = QLabel("la puissance du "
                          f"<span style='color:{color('accent')};font-weight:700'>groupe</span>")
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
        act = color("action")
        self.model_card.setStyleSheet(
            f"#modelInvite {{ background: {_rgba(act, 0.08)}; "
            f"border: 1px solid {_rgba(act, 0.45)}; border-radius: 10px; }}")
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

        split.addWidget(hero, 5)
        split.addWidget(right, 6)
        root.addWidget(split_host, 1)

    def _dismiss(self):
        self.model_card.setVisible(False)
        if self._on_dismiss is not None:
            self._on_dismiss()

    def set_model_available(self, available: bool):
        self.model_card.setVisible(not available)
