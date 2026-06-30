from PySide6.QtWidgets import QWidget


class SettingsScreen(QWidget):
    def __init__(self, ref, prefs, on_apply, on_back):
        super().__init__()
