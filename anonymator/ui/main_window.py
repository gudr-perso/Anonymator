# anonymator/ui/main_window.py
from pathlib import Path
from PySide6.QtWidgets import QMainWindow, QStackedWidget
from anonymator.referential import Referential
from anonymator.ui.preferences import Preferences
from anonymator.ui.theme import build_qss
from anonymator.ui.model_loader import ModelLoader
from anonymator.ui.home_screen import HomeScreen
from anonymator.ui.text_screen import TextScreen
from anonymator.ui.file_screen import FileScreen
from anonymator.ui.settings_screen import SettingsScreen
from anonymator.ui.setup_screen import SetupScreen
from anonymator.core.model_status import is_model_available

PREFS_PATH = Path.home() / ".anonymator" / "preferences.json"


class MainWindow(QMainWindow):
    def __init__(self, loader: ModelLoader | None = None,
                 prefs_path: Path = PREFS_PATH,
                 skip_setup: bool = False):
        super().__init__()
        self.setWindowTitle("Anonymator")
        self.prefs_path = prefs_path
        self.prefs = Preferences.load(prefs_path)
        self.ref = Referential.load_default()
        self.loader = loader or ModelLoader()

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.setup_screen = SetupScreen()
        self.home = HomeScreen(self.show_text, self.show_file, self.show_settings)
        self.text_screen = TextScreen(self.ref, self.loader, self.prefs, self.show_home)
        self.file_screen = FileScreen(self.ref, self.loader, self.prefs, self.show_home)
        self.settings_screen = SettingsScreen(self.ref, self.prefs,
                                              self._apply_prefs, self.show_home)
        for w in (self.setup_screen, self.home, self.text_screen,
                  self.file_screen, self.settings_screen):
            self.stack.addWidget(w)

        self.setup_screen.model_ready.connect(self.show_home)

        if skip_setup or is_model_available():
            self.show_home()
        else:
            self.stack.setCurrentWidget(self.setup_screen)

        self._apply_theme()

    def _apply_theme(self):
        self.setStyleSheet(build_qss(self.prefs.theme))

    def _apply_prefs(self):
        self.prefs.save(self.prefs_path)
        self._apply_theme()

    def show_home(self):
        self.stack.setCurrentWidget(self.home)

    def show_text(self):
        self.stack.setCurrentWidget(self.text_screen)

    def show_file(self):
        self.stack.setCurrentWidget(self.file_screen)

    def show_settings(self):
        self.stack.setCurrentWidget(self.settings_screen)
