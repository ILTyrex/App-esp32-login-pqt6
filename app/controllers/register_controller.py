from PyQt6 import uic
from PyQt6.QtWidgets import QMainWindow, QMessageBox


class RegisterController(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("app/gui/register.ui", self)

        # Widgets
        self.inputUser = self.findChild(type(self.inputUser), "inputUser")
        self.inputPassword = self.findChild(type(self.inputPassword), "inputPassword")
        self.inputConfirmPassword = self.findChild(type(self.inputConfirmPassword), "inputConfirmPassword")
        self.btnRegister = self.findChild(type(self.btnRegister), "btnRegister")
        self.textLogin = self.findChild(type(self.textLogin), "textLogin")

        # Conexiones
        self.btnRegister.clicked.connect(self.handle_register)
        self.textLogin.mousePressEvent = self.go_to_login

    def handle_register(self):
        """Valida datos de registro"""
        user = self.inputUser.text().strip()
        pwd = self.inputPassword.text().strip()
        confirm = self.inputConfirmPassword.text().strip()

        if not user or not pwd or not confirm:
            QMessageBox.warning(self, "Error", "Todos los campos son obligatorios")
            return

        if pwd != confirm:
            QMessageBox.warning(self, "Error", "Las contraseñas no coinciden")
            return

        QMessageBox.information(self, "Éxito", f"Usuario {user} registrado 🚀")
        self.go_to_login(None)

    def go_to_login(self, event):
        """Volver al login"""
        from app.controllers.login_controller import LoginController  # 👈 Import aquí
        self.login_window = LoginController()
        self.login_window.show()
        self.close()
