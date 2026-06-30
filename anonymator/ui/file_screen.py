from PySide6.QtWidgets import QWidget


class FileScreen(QWidget):
    def __init__(self, ref, loader, prefs, on_back):
        super().__init__()
