"""Invitation à s'enregistrer, proposée au lancement.

Objectif : savoir qui utilise l'application, sans jamais la bloquer.

- **Non bloquant** : « Plus tard » et « Ne plus demander » sont toujours offerts,
  et l'invitation n'apparaît qu'aux lancements `ASK_AT_LAUNCHES`.
- **Aucun appel réseau** : « M'enregistrer » ouvre le formulaire dans le
  navigateur par défaut. L'application n'envoie rien elle-même — la promesse
  « aucune donnée ne quitte votre machine » reste vraie. Ce module ne doit donc
  importer aucune bibliothèque réseau (vérifié par tests/test_registration.py).
- **Par édition** : chaque marque a son formulaire (`Brand.form_url`) ; une
  édition sans formulaire n'affiche pas l'invitation.
"""
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QLayout, QPushButton,
                               QVBoxLayout)

from anonymator.brand import active_brand

REGISTER, LATER, NEVER = "register", "later", "never"

# Lancements auxquels l'invitation est proposée tant que rien n'est décidé :
# le premier, puis une relance. Ensuite on n'insiste plus.
ASK_AT_LAUNCHES = (1, 5)


class _Paragraph(QLabel):
    """Paragraphe à largeur fixe dont la hauteur suit la police effective.

    Quand le titre est plus large que le paragraphe (« Bienvenue dans
    Cum'Anonyme »), la mise en page demande la hauteur pour la largeur
    *disponible* et non pour la largeur réelle : un paragraphe de 3 lignes
    recevait la hauteur de 2 et le texte était coupé en haut et en bas."""
    def __init__(self, text: str, width: int):
        super().__init__(text)
        self.setWordWrap(True)
        self.setFixedWidth(width)

    def heightForWidth(self, width: int) -> int:
        return super().heightForWidth(min(width, self.maximumWidth()))


class RegistrationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        name = active_brand().product_name
        self.setWindowTitle(f"Bienvenue dans {name}")
        self.choice = LATER          # fermer la fenêtre = « Plus tard »

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20); root.setSpacing(12)
        root.setSizeConstraint(QLayout.SetFixedSize)   # la fenêtre suit son contenu
        title = QLabel(f"Bienvenue dans {name}"); title.setObjectName("title")
        root.addWidget(title)
        for text in (
            f"{name} est gratuit et le restera. Pour savoir qui l'utilise et "
            "l'adapter à vos besoins, nous vous invitons à vous enregistrer "
            "(1 minute).",
            "Le formulaire s'ouvre dans votre navigateur. L'application, elle, "
            "n'envoie rien : vos documents restent sur votre poste.",
        ):
            root.addWidget(_Paragraph(text, 440))

        row = QHBoxLayout(); row.addStretch()
        self.never_btn = QPushButton("Ne plus demander"); self.never_btn.setObjectName("ghost")
        self.later_btn = QPushButton("Plus tard"); self.later_btn.setObjectName("secondary")
        self.register_btn = QPushButton("M'enregistrer"); self.register_btn.setObjectName("primary")
        self.register_btn.setDefault(True)
        for btn, choice in ((self.never_btn, NEVER), (self.later_btn, LATER),
                            (self.register_btn, REGISTER)):
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _=False, c=choice: self._choose(c))
            row.addWidget(btn)
        root.addLayout(row)

    def _choose(self, choice: str) -> None:
        self.choice = choice
        self.accept()


def _ask_with_dialog(parent) -> str:
    dlg = RegistrationDialog(parent)
    dlg.exec()
    return dlg.choice


def _open_in_browser(url: str) -> None:
    QDesktopServices.openUrl(QUrl(url))


def registration_url() -> str | None:
    return active_brand().form_url


def should_prompt(prefs) -> bool:
    return prefs.registration == "pending" and prefs.launch_count in ASK_AT_LAUNCHES


def maybe_prompt(parent, prefs, save, open_url=None, ask=None) -> None:
    """À appeler une fois par lancement. Compte le lancement, propose
    l'invitation si c'est le moment, applique et sauvegarde le choix."""
    open_url = open_url or _open_in_browser
    ask = ask or _ask_with_dialog
    url = registration_url()
    if url is None or prefs.registration != "pending":
        return
    if prefs.launch_count <= max(ASK_AT_LAUNCHES):   # inutile de compter au-delà
        prefs.launch_count += 1
    if should_prompt(prefs):
        choice = ask(parent)
        if choice == REGISTER:
            open_url(url)
            prefs.registration = "done"
        elif choice == NEVER:
            prefs.registration = "never"
    save()
