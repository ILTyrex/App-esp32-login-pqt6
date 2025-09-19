import sys
import os
from PyQt6.QtWidgets import QApplication

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.controllers.login_controller import LoginController


def main():
    app = QApplication(sys.argv)

    # Creamos y mostramos la ventana de login
    login_window = LoginController()
    login_window.show()

    # Ejecutamos la app
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
