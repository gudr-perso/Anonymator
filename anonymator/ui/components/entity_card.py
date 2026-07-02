from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel
from PySide6.QtCore import Signal
from anonymator.ui.icons import icon
from anonymator.ui.components.toggle import ToggleSwitch
from anonymator.ui.entity_meta import ENTITY_META
from anonymator.ui.colors import color_for


class EntityCard(QFrame):
    """Mini-carte d'un type d'entité : icône + libellé + sous-titre + toggle."""
    toggled = Signal(str, bool)

    def __init__(self, code: str, active: bool, parent=None):
        super().__init__(parent)
        self.code = code
        self.setObjectName("EntityCard")
        meta = ENTITY_META[code]
        row = QHBoxLayout(self)
        row.setContentsMargins(14, 12, 14, 12)
        ic = QLabel()
        ic.setPixmap(icon(meta.icon, color_for(code), 20).pixmap(20, 20))
        col = QVBoxLayout(); col.setSpacing(1)
        t = QLabel(meta.label); t.setStyleSheet("font-weight: 700;")
        s = QLabel(meta.subtitle); s.setObjectName("muted"); s.setStyleSheet("font-size: 12px;")
        col.addWidget(t); col.addWidget(s)
        self.toggle = ToggleSwitch(); self.toggle.setChecked(active)
        self.toggle.toggled.connect(lambda on: self.toggled.emit(self.code, on))
        row.addWidget(ic); row.addSpacing(6); row.addLayout(col); row.addStretch()
        row.addWidget(self.toggle)
