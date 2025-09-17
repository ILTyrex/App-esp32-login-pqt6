import sys
from PyQt6.QtWidgets import QApplication
from app.controllers.login_controller import LoginController


def main():
    app = QApplication(sys.argv)

    login_window = LoginController()
    login_window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
