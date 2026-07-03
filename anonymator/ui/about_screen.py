from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QScrollArea)
from PySide6.QtGui import QPixmap, QDesktopServices
from PySide6.QtCore import Qt, QUrl
from anonymator.ui.components.header import HeaderBand
from anonymator.ui.components.nav_band import NavBand
from anonymator.ui.components.cards import Card
from anonymator.ui.icons import icon
from anonymator.ui.theme import color
from anonymator import __version__
from anonymator.ui.about import REPO_URL

EMBEDDED_COMPONENTS = [
    ("PyMuPDF", "© Artifex Software · lecture & écriture PDF", "AGPL-3.0", "#d62828"),
    ("GLiNER", "urchade/gliner_multi-v2.1 · détection d'entités", "Apache-2.0", "#00965E"),
]


def _strong(text: str) -> QLabel:
    l = QLabel(text); l.setStyleSheet("font-weight: 700;"); return l


def _muted(text: str) -> QLabel:
    l = QLabel(text); l.setObjectName("muted"); return l


def _icon_label(name: str) -> QLabel:
    l = QLabel(); l.setPixmap(icon(name, color("action"), 20).pixmap(20, 20)); return l


def _license_badge(text: str, color: str) -> QLabel:
    b = QLabel(text); b.setAlignment(Qt.AlignCenter)
    b.setStyleSheet(f"color: {color}; border: 1px solid {color}; border-radius: 8px;"
                    f"padding: 2px 9px; font-size: 11px; font-weight: 700;")
    return b


class AboutScreen(QWidget):
    def __init__(self, on_back):
        super().__init__()
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)
        root.addWidget(HeaderBand())
        root.addWidget(NavBand("À propos", "sparkle", on_home=on_back))

        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QScrollArea.NoFrame)
        host = QWidget(); body = QVBoxLayout(host)
        body.setContentsMargins(40, 20, 40, 40); body.setSpacing(16)
        scroll.setWidget(host); root.addWidget(scroll)

        # Héros centré
        hero = QVBoxLayout(); hero.setAlignment(Qt.AlignHCenter)
        logo_path = Path(__file__).parent / "assets" / color("logo")
        if logo_path.exists():
            logo = QLabel(); logo.setAlignment(Qt.AlignHCenter)
            # Borne largeur ET hauteur : le logo CAP est carré (1024²), le logo
            # CUMA large et court — KeepAspectRatio évite le rognage dans les deux cas.
            pix = QPixmap(str(logo_path)).scaled(
                260, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo.setPixmap(pix)
            logo.setFixedHeight(pix.height())   # réserve la hauteur exacte → plus de rognage
            hero.addWidget(logo, alignment=Qt.AlignHCenter)
        name_row = QHBoxLayout(); name_row.setAlignment(Qt.AlignHCenter)
        name = QLabel("Anonymator"); name.setObjectName("title")
        self.version_badge = QLabel(f"v{__version__}"); self.version_badge.setObjectName("occBadge")
        name_row.addWidget(name); name_row.addWidget(self.version_badge)
        hero.addLayout(name_row)
        pitch = QLabel("Anonymisez vos textes et fichiers en local. Protégez les "
                       "données personnelles avant tout partage, sans rien envoyer en ligne.")
        pitch.setObjectName("muted"); pitch.setWordWrap(True); pitch.setAlignment(Qt.AlignHCenter)
        pitch.setMaximumWidth(680)
        hero.addWidget(pitch, alignment=Qt.AlignHCenter)
        body.addLayout(hero)

        # Carte licence
        lic = Card("scale", "Licence & code source")
        r1 = QHBoxLayout()
        r1.addWidget(_icon_label("scale"))
        col1 = QVBoxLayout()
        col1.addWidget(_strong("AGPL-3.0")); col1.addWidget(_muted("Logiciel libre — copyleft"))
        r1.addLayout(col1); r1.addStretch()
        lic.body.addLayout(r1)
        gh = QPushButton(f"  Code source sur GitHub — tag v{__version__}")
        gh.setObjectName("secondary"); gh.setIcon(icon("github", color("text"), 18))
        gh.setCursor(Qt.PointingHandCursor)
        gh.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(REPO_URL)))
        lic.body.addWidget(gh)
        body.addWidget(lic)

        # Carte composants
        comp = Card("package", "Composants embarqués")
        for pkg, desc, lbl, col in EMBEDDED_COMPONENTS:
            r = QHBoxLayout()
            r.addWidget(_icon_label("package"))
            c = QVBoxLayout(); c.addWidget(_strong(pkg)); c.addWidget(_muted(desc))
            r.addLayout(c); r.addStretch(); r.addWidget(_license_badge(lbl, col))
            comp.body.addLayout(r)
        body.addWidget(comp)
        body.addStretch()
