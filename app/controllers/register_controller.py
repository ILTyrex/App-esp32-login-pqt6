# app/controllers/register_controller.py
from PyQt6 import uic
from PyQt6.QtWidgets import QMainWindow, QMessageBox, QLineEdit, QPushButton, QLabel
from PyQt6.QtCore import QThread
from app.workers.db_worker import DBWorker

class RegisterController(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("app/gui/register.ui", self)

        # Widgets (aseguramos tipo correcto)
        self.inputUser: QLineEdit = self.findChild(QLineEdit, "inputUser")
        self.inputPassword: QLineEdit = self.findChild(QLineEdit, "inputPassword")
        self.inputConfirmPassword: QLineEdit = self.findChild(QLineEdit, "inputConfirmPassword")
        self.btnRegister: QPushButton = self.findChild(QPushButton, "btnRegister")
        self.textLogin: QLabel = self.findChild(QLabel, "textLogin")

        # Conexiones
        self.btnRegister.clicked.connect(self.handle_register)
        self.textLogin.mousePressEvent = self.go_to_login

        # Placeholders
        self.thread = None
        self.worker = None

    def handle_register(self):
        """Valida datos de registro y lanza worker en un hilo separado"""
        user = self.inputUser.text().strip()
        pwd = self.inputPassword.text().strip()
        confirm = self.inputConfirmPassword.text().strip()

        if not user or not pwd or not confirm:
            QMessageBox.warning(self, "Error", "Todos los campos son obligatorios")
            return

        if pwd != confirm:
            QMessageBox.warning(self, "Error", "Las contraseñas no coinciden")
            return

        # Crear thread y worker
        self.thread = QThread(self)
        self.worker = DBWorker(user, pwd)
        self.worker.moveToThread(self.thread)

        # Conexiones
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_register_finished)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        # Iniciar hilo
        self.thread.start()

    def on_register_finished(self, success, msg):
        """Callback cuando el worker termina"""
        if success:
            QMessageBox.information(self, "Éxito", msg)
            self.go_to_login(None)
        else:
            QMessageBox.critical(self, "Error", msg)

    def go_to_login(self, event):
        from app.controllers.login_controller import LoginController
        self.login_window = LoginController()
        self.login_window.show()
        self.hide()
