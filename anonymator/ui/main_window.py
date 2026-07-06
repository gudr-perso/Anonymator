# anonymator/ui/main_window.py
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMainWindow, QStackedWidget
from anonymator.referential import Referential
from anonymator.ui.preferences import Preferences
from anonymator.user_rules import UserRules
from anonymator.ui.theme import build_qss, set_active_theme, active_theme
from anonymator.brand import active_brand
from anonymator.ui.model_loader import ModelLoader
from anonymator.ui.home_screen import HomeScreen
from anonymator.ui.text_screen import TextScreen
from anonymator.ui.file_screen import FileScreen
from anonymator.ui.pdf_screen import PdfScreen
from anonymator.ui.settings_screen import SettingsScreen
from anonymator.ui.rules_screen import RulesScreen
from anonymator.ui.about_screen import AboutScreen
from anonymator.core.model_status import is_model_available

_ASSETS = Path(__file__).parent / "assets"

PREFS_PATH = Path.home() / ".anonymator" / "preferences.json"


class MainWindow(QMainWindow):
    def __init__(self, loader: ModelLoader | None = None,
                 prefs_path: Path = PREFS_PATH):
        super().__init__()
        self.setWindowTitle(active_brand().product_name)
        ico = _ASSETS / "anonymator.ico"
        if ico.exists():
            self.setWindowIcon(QIcon(str(ico)))
        self.prefs_path = prefs_path
        self.prefs = Preferences.load(prefs_path)
        self.rules_path = prefs_path.parent / "user_rules.json"
        self.ref = self._build_ref()
        self.loader = loader or ModelLoader()

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        set_active_theme(self._effective_theme())   # avant de construire la couche peinte/icônes
        self._build_screens()
        self.show_home()
        self._apply_theme()

    def _build_screens(self):
        """(Re)construit tous les écrans avec le thème actif courant."""
        while self.stack.count():
            w = self.stack.widget(0)
            self.stack.removeWidget(w)
            w.deleteLater()

        self.home = HomeScreen(self.show_text, self.show_file, self.show_settings,
                               model_available=is_model_available(),
                               on_download=self._request_model,
                               on_pdf=self.show_pdf,
                               on_rules=self.show_rules, on_about=self.show_about)
        self.text_screen = TextScreen(self.ref, self.loader, self.prefs,
                                      self.show_home, on_request_model=self._request_model)
        self.file_screen = FileScreen(self.ref, self.loader, self.prefs,
                                      self.show_home, on_text_review=self._review_text,
                                      on_request_model=self._request_model)
        self.pdf_screen = PdfScreen(self.ref, self.loader, self.prefs,
                                    self.show_home, on_request_model=self._request_model)
        self.settings_screen = SettingsScreen(self.ref, self.prefs,
                                              self._apply_prefs, self.show_home)
        self.rules_screen = RulesScreen(self.rules_path, self._apply_prefs, self.show_home)
        self.about_screen = AboutScreen(self.show_home)
        for w in (self.home, self.text_screen, self.file_screen,
                  self.pdf_screen, self.settings_screen,
                  self.rules_screen, self.about_screen):
            self.stack.addWidget(w)

        self.settings_screen.model_ready.connect(self._on_model_ready)

    def _build_ref(self):
        ref = Referential.load_default(overrides=self.prefs.entity_overrides)
        # migration one-shot : la stoplist (éditée ou par défaut) alimente user_rules.json
        fallback = self.prefs.ner_stoplist
        if fallback is None:
            fallback = ref.stoplist_terms()
        rules = UserRules.load(self.rules_path, fallback_terms=fallback)
        return ref.with_user_rules(rules)

    def _effective_theme(self) -> str:
        """Thème réellement appliqué : celui de la marque si verrouillée,
        sinon la préférence utilisateur (mode dev)."""
        b = active_brand()
        return b.theme if b.locked else self.prefs.theme

    def _apply_theme(self):
        theme = self._effective_theme()
        set_active_theme(theme)
        self.setStyleSheet(build_qss(theme))

    def _apply_prefs(self):
        theme_changed = self._effective_theme() != active_theme()
        self.prefs.save(self.prefs_path)
        self.ref = self._build_ref()
        self.text_screen.ref = self.ref
        self.file_screen.ref = self.ref
        self.pdf_screen.ref = self.ref
        self._apply_theme()
        if theme_changed:
            # reconstruire hors du callback du combo (évite de détruire le
            # settings_screen dont le signal est en cours d'exécution)
            QTimer.singleShot(0, self._retheme)

    def _retheme(self):
        self._build_screens()
        self.show_home()

    def _request_model(self):
        self.show_settings()
        self.settings_screen.start_model_download()

    def _on_model_ready(self):
        self.home.set_model_available(True)
        self.text_screen.hide_degraded()
        self.file_screen.hide_degraded()
        self.pdf_screen.hide_degraded()

    def closeEvent(self, event):
        # SettingsScreen est un enfant du QStackedWidget : son closeEvent ne se
        # déclenche pas ici → on arrête explicitement un éventuel téléchargement.
        self.settings_screen.stop_download()
        super().closeEvent(event)

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

    def show_pdf(self):
        self.stack.setCurrentWidget(self.pdf_screen)

    def show_settings(self):
        self.stack.setCurrentWidget(self.settings_screen)

    def show_rules(self):
        self.stack.setCurrentWidget(self.rules_screen)

    def show_about(self):
        self.stack.setCurrentWidget(self.about_screen)
