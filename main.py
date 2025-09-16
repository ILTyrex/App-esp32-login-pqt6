import sys
from PyQt6.QtWidgets import QApplication
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
