import os
import sys
import tempfile
import traceback
from datetime import datetime
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMessageBox
from anonymator.ui.main_window import MainWindow

_CRASH_LOG = Path(tempfile.gettempdir()) / "anonymator-crash.log"


def _excepthook(exc_type, exc, tb) -> None:
    """Filet de sécurité : toute exception non gérée (y compris sur le thread
    principal, dans un slot Qt) est journalisée ET affichée dans un dialogue.
    Sans ce hook, l'exe *windowed* redirige stderr vers devnull et l'erreur
    disparaît en silence (« rien ne se passe »)."""
    detail = "".join(traceback.format_exception(exc_type, exc, tb))
    try:
        with open(_CRASH_LOG, "a", encoding="utf-8") as f:
            f.write(f"\n===== {datetime.now().isoformat(timespec='seconds')} =====\n")
            f.write(detail)
    except Exception:   # noqa: BLE001 — la journalisation ne doit jamais masquer l'erreur d'origine
        pass
    if QApplication.instance() is not None:
        QMessageBox.critical(
            None, "Erreur inattendue",
            f"Une erreur inattendue s'est produite :\n\n{exc_type.__name__} : {exc}\n\n"
            f"Le détail technique a été enregistré dans :\n{_CRASH_LOG}")
    else:   # pas d'IHM disponible : dernier recours sur le flux d'origine
        sys.__stderr__ and sys.__stderr__.write(detail)


def install_excepthook() -> None:
    sys.excepthook = _excepthook


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
