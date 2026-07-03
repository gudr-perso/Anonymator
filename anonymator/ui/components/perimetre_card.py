from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from anonymator.files import ooxml
from anonymator.ui.theme import color


class PerimetreCard(QFrame):
    """Encart persistant listant ce qui est traité et ce qui ne l'est pas,
    à partir de la constante ooxml.COVERAGE (source de vérité unique)."""

    def __init__(self):
        super().__init__()
        self.setObjectName("PerimetreCard")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(4)
        traite = "".join(f"• {x}<br>" for x in ooxml.COVERAGE["traite"])
        non = "".join(f"• {x}<br>" for x in ooxml.COVERAGE["non_traite"])
        self._html = (
            f"<b style='color:{color('action')}'>✅ Traité</b><br>{traite}"
            f"<br><b>⚠️ Non traité — à vérifier manuellement</b><br>{non}"
        )
        label = QLabel(self._html)
        label.setTextFormat(Qt.RichText)
        label.setWordWrap(True)
        lay.addWidget(label)

    def rendered_text(self) -> str:
        """Texte brut (pour tests) : items sans balises."""
        return self._html
