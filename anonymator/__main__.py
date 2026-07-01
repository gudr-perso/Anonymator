import os
import sys
from PySide6.QtWidgets import QApplication
from anonymator.ui.main_window import MainWindow


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
    win = build_window()
    win.resize(900, 700)
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
