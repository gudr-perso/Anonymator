import sys
from PySide6.QtWidgets import QApplication
from anonymator.ui.main_window import MainWindow


def build_window() -> MainWindow:
    return MainWindow()


def main() -> int:
    app = QApplication(sys.argv)
    win = build_window()
    win.resize(900, 700)
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
