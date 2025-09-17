import sys
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import QTimer

try:
    from app.controllers.login_controller import LoginController
except Exception:
    LoginController = None

try:
    from main_window import MainWindow
except Exception:
    MainWindow = None


def close_orphan_windows():
    app = QApplication.instance()
    if app is None:
        return
    for w in list(app.topLevelWidgets()):
        try:
            if not isinstance(w, QWidget):
                continue
            title = (w.windowTitle() or "").strip()
            wsize = w.size()
            if title == "" and wsize.width() <= 160 and wsize.height() <= 160:
                w.close()
        except Exception:
            pass


def main():
    app = QApplication(sys.argv)

    if LoginController is not None:
        login_win = LoginController()
        login_win.show()
        QTimer.singleShot(200, close_orphan_windows)
        sys.exit(app.exec())
        return

    if MainWindow is not None:
        w = MainWindow(username="local")
        w.show()
        QTimer.singleShot(200, close_orphan_windows)
        sys.exit(app.exec())

    print("No UI available: neither LoginController nor MainWindow could be imported.")


if __name__ == "__main__":
    main()
