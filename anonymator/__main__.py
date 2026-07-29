import os
import sys
import tempfile
import threading
import traceback
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QApplication, QMessageBox
from anonymator.ui.main_window import MainWindow

_CRASH_LOG = Path(tempfile.gettempdir()) / "anonymator-crash.log"


class _ErrorReporter(QObject):
    """Affiche les erreurs *depuis le thread GUI*.

    `sys.excepthook` peut être appelé depuis n'importe quel thread (le worker de
    téléchargement, notamment). Construire un QMessageBox hors du thread GUI est
    un comportement indéfini côté Qt : le dialogue bloquait le worker et figeait
    l'application. Le signal fait la bascule (connexion mise en file d'attente
    dès que l'émetteur n'est pas le thread GUI)."""
    failed = Signal(str)

    def __init__(self):
        super().__init__()
        self.failed.connect(self._show)

    @Slot(str)
    def _show(self, text: str) -> None:
        QMessageBox.critical(None, "Erreur inattendue", text)


_reporter: _ErrorReporter | None = None
_reporter_lock = threading.Lock()


def _gui_reporter(app: QApplication) -> _ErrorReporter:
    """Rapporteur unique, rattaché au thread GUI même s'il est créé ailleurs."""
    global _reporter
    with _reporter_lock:
        if _reporter is None:
            _reporter = _ErrorReporter()
            _reporter.moveToThread(app.thread())
        return _reporter


def _excepthook(exc_type, exc, tb) -> None:
    """Filet de sécurité : toute exception non gérée (y compris sur le thread
    principal, dans un slot Qt) est journalisée ET affichée dans un dialogue.
    Sans ce hook, l'exe *windowed* redirige stderr vers devnull et l'erreur
    disparaît en silence (« rien ne se passe »).

    La journalisation est synchrone quel que soit le thread ; seul l'affichage
    est reposté sur le thread GUI."""
    detail = "".join(traceback.format_exception(exc_type, exc, tb))
    try:
        with open(_CRASH_LOG, "a", encoding="utf-8") as f:
            f.write(f"\n===== {datetime.now().isoformat(timespec='seconds')} =====\n")
            f.write(detail)
    except Exception:   # noqa: BLE001 — la journalisation ne doit jamais masquer l'erreur d'origine
        pass
    app = QApplication.instance()
    if app is not None:
        _gui_reporter(app).failed.emit(
            f"Une erreur inattendue s'est produite :\n\n{exc_type.__name__} : {exc}\n\n"
            f"Le détail technique a été enregistré dans :\n{_CRASH_LOG}")
    else:   # pas d'IHM disponible : dernier recours sur le flux d'origine
        sys.__stderr__ and sys.__stderr__.write(detail)


def install_excepthook() -> None:
    sys.excepthook = _excepthook
    if (app := QApplication.instance()) is not None:
        _gui_reporter(app)      # créé dans le thread GUI, avant tout incident


def ensure_std_streams() -> None:
    """Dans un exe PyInstaller *windowed*, sys.stdout/sys.stderr valent None.
    tqdm (progression du téléchargement) et diverses libs écrivent dessus et
    lèveraient « 'NoneType' object has no attribute 'write' ». On redirige vers
    os.devnull le cas échéant."""
    if sys.stdout is not None and sys.stderr is not None:
        return
    devnull = open(os.devnull, "w")
    if sys.stdout is None:
        sys.stdout = devnull
    if sys.stderr is None:
        sys.stderr = devnull


def build_window() -> MainWindow:
    return MainWindow()


def main() -> int:
    ensure_std_streams()
    app = QApplication(sys.argv)
    install_excepthook()
    win = build_window()
    win.resize(900, 700)
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
