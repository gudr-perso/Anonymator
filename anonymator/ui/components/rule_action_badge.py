from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy
from anonymator.ui.icons import icon


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


class RuleActionBadge(QFrame):
    """Pastille colorée (icône + libellé) pour l'action d'une règle.

    action ∈ {'keep','mask'}. On utilise une vraie icône SVG (œil / œil barré)
    plutôt qu'un emoji : Qt mesure mal la largeur des emoji couleur, ce qui
    rognait le badge dans une colonne ResizeToContents."""
    _KEEP = "#00965E"
    _MASK = "#E8621A"

    def __init__(self, action: str, parent=None):
        super().__init__(parent)
        keep = action == "keep"
        self.action = action
        self.color = self._KEEP if keep else self._MASK
        self._text = "Ne jamais masquer" if keep else "Toujours masquer"
        icon_name = "eye" if keep else "eye-off"

        self.setObjectName("RuleBadge")
        # Taille fixe : la pastille ne se compresse jamais sous son contenu,
        # sinon le libellé serait rogné dans une colonne étroite.
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setStyleSheet(
            f"#RuleBadge {{ background: {_rgba(self.color, 0.14)}; border-radius: 8px; }}")
        row = QHBoxLayout(self)
        row.setContentsMargins(10, 3, 10, 3)
        row.setSpacing(6)
        ic = QLabel()
        ic.setPixmap(icon(icon_name, self.color, 14).pixmap(14, 14))
        ic.setStyleSheet("background: transparent;")
        self._label = QLabel(self._text)
        self._label.setStyleSheet(
            f"color: {self.color}; font-size: 12px; font-weight: 700; background: transparent;")
        # Plancher de largeur = sizeHint : le libellé ne peut jamais être rogné,
        # quelle que soit la police de la plateforme.
        self._label.setMinimumWidth(self._label.sizeHint().width())
        row.addWidget(ic)
        row.addWidget(self._label)

    def text(self) -> str:
        """Libellé de l'action (API pratique pour les tests)."""
        return self._text
