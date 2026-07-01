# anonymator/ui/main_window.py
from pathlib import Path
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMainWindow, QStackedWidget
from anonymator.referential import Referential
from anonymator.ui.preferences import Preferences
from anonymator.ui.theme import build_qss
from anonymator.ui.model_loader import ModelLoader
from anonymator.ui.home_screen import HomeScreen
from anonymator.ui.text_screen import TextScreen
from anonymator.ui.file_screen import FileScreen
from anonymator.ui.settings_screen import SettingsScreen
from anonymator.core.model_status import is_model_available

_ASSETS = Path(__file__).parent / "assets"

PREFS_PATH = Path.home() / ".anonymator" / "preferences.json"


class MainWindow(QMainWindow):
    def __init__(self, loader: ModelLoader | None = None,
                 prefs_path: Path = PREFS_PATH):
        super().__init__()
        self.setWindowTitle("Anonymator")
        ico = _ASSETS / "anonymator.ico"
        if ico.exists():
            self.setWindowIcon(QIcon(str(ico)))
        self.prefs_path = prefs_path
        self.prefs = Preferences.load(prefs_path)
        self.ref = self._build_ref()
        self.loader = loader or ModelLoader()

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.home = HomeScreen(self.show_text, self.show_file, self.show_settings,
                               model_available=is_model_available(),
                               on_download=self._request_model)
        self.text_screen = TextScreen(self.ref, self.loader, self.prefs,
                                      self.show_home, on_request_model=self._request_model)
        self.file_screen = FileScreen(self.ref, self.loader, self.prefs,
                                      self.show_home, on_text_review=self._review_text,
                                      on_request_model=self._request_model)
        self.settings_screen = SettingsScreen(self.ref, self.prefs,
                                              self._apply_prefs, self.show_home)
        for w in (self.home, self.text_screen, self.file_screen, self.settings_screen):
            self.stack.addWidget(w)

        self.settings_screen.model_ready.connect(self._on_model_ready)

        self.show_home()
        self._apply_theme()

    def _build_ref(self):
        ref = Referential.load_default(overrides=self.prefs.entity_overrides)
        if self.prefs.ner_stoplist is not None:
            ref = ref.with_stoplist(self.prefs.ner_stoplist)
        return ref

    def _apply_theme(self):
        self.setStyleSheet(build_qss(self.prefs.theme))

    def _apply_prefs(self):
        self.prefs.save(self.prefs_path)
        self.ref = self._build_ref()
        self.text_screen.ref = self.ref
        self.file_screen.ref = self.ref
        self._apply_theme()

    def _request_model(self):
        self.show_settings()
        self.settings_screen.start_model_download()

    def _on_model_ready(self):
        self.home.set_model_available(True)
        self.text_screen.hide_degraded()
        self.file_screen.hide_degraded()

    def _review_text(self, text: str):
        self.text_screen.input.setPlainText(text)
        self.stack.setCurrentWidget(self.text_screen)
        self.text_screen.analyze()

    def show_home(self):
        self.stack.setCurrentWidget(self.home)

    def show_text(self):
        self.stack.setCurrentWidget(self.text_screen)

    def show_file(self):
        self.stack.setCurrentWidget(self.file_screen)

    def show_settings(self):
        self.stack.setCurrentWidget(self.settings_screen)
