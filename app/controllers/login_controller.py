from PyQt6 import uic
from PyQt6.QtWidgets import QMainWindow, QMessageBox
from PyQt6.QtCore import Qt


class LoginController(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("app/gui/login.ui", self)

        # Widgets
        self.inputUser = self.findChild(type(self.inputUser), "inputUser")
        self.inputPassword = self.findChild(type(self.inputPassword), "inputPassword")
        self.btnLogin = self.findChild(type(self.btnLogin), "btnLogin")
        self.textRegister = self.findChild(type(self.textRegister), "textRegister")

        # Conexiones
        self.btnLogin.clicked.connect(self.handle_login)
        self.textRegister.mousePressEvent = self.go_to_register  # Captura click

    def handle_login(self):
        """Valida usuario y contraseña"""
        username = self.inputUser.text().strip()
        password = self.inputPassword.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Error", "Por favor ingresa usuario y contraseña")
            return

        if username == "admin" and password == "1234":
            QMessageBox.information(self, "Éxito", "Login correcto 🚀")
            self.close()
        else:
            QMessageBox.critical(self, "Error", "Usuario o contraseña incorrectos")

    def go_to_register(self, event):
        """Abrir ventana de registro"""
        from app.controllers.register_controller import RegisterController  # 👈 Import aquí
        self.register_window = RegisterController()
        self.register_window.show()
        self.close()
