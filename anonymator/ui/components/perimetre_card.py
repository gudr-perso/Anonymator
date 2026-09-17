from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from anonymator.files import ooxml
from anonymator.ui.theme import color


class PerimetreCard(QFrame):
    """Encart persistant listant ce qui est traité et ce qui ne l'est pas,
    à partir de ooxml.COVERAGE_BY_FORMAT (source de vérité unique).

    Le périmètre dépend du format : un classeur ne porte ni zone de texte ni
    note de bas de page, mais des commentaires de cellule et des en-têtes de
    feuille que le document n'a pas. L'encart n'était affiché que pour les
    documents, donc l'utilisateur d'un classeur ne recevait aucune indication
    de ce qui échappait au traitement."""

    def __init__(self, fmt: str = "docx"):
        super().__init__()
        self.setObjectName("PerimetreCard")
        self.fmt = fmt
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(4)
        self._label = QLabel("")
        self._label.setTextFormat(Qt.RichText)
        self._label.setWordWrap(True)
        lay.addWidget(self._label)
        self.set_format(fmt)

    def set_format(self, fmt: str) -> None:
        coverage = ooxml.COVERAGE_BY_FORMAT.get(fmt, ooxml.COVERAGE_DOCX)
        self.fmt = fmt
        traite = "".join(f"• {x}<br>" for x in coverage["traite"])
        non = "".join(f"• {x}<br>" for x in coverage["non_traite"])
        self._html = (
            f"<b style='color:{color('action')}'>✅ Traité</b><br>{traite}"
            f"<br><b>⚠️ Non traité — à vérifier manuellement</b><br>{non}")
        self._label.setText(self._html)

    def rendered_text(self) -> str:
        """Texte brut (pour tests) : texte affiché, balises comprises."""
        return self._html
