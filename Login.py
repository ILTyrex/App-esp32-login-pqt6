# Login.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QHBoxLayout, QPushButton, QLabel, QMessageBox
)
from PyQt6.QtCore import Qt

class LoginDialog(QDialog):
    """
    Login simple en memoria. Usuarios se mantienen en self._users (dict).
    Usuario por defecto: admin / admin
    Los registros no se persisten (temporal en memoria).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Login")
        self.setModal(True)
        self.resize(360, 160)

        # usuarios en memoria
        self._users = {"admin": "admin"}

        layout = QVBoxLayout()
        form = QFormLayout()
        self.user_edit = QLineEdit()
        self.pwd_edit = QLineEdit()
        self.pwd_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Usuario:", self.user_edit)
        form.addRow("Contraseña:", self.pwd_edit)
        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        self.login_btn = QPushButton("Entrar")
        self.register_btn = QPushButton("Registrar")
        self.cancel_btn = QPushButton("Cancelar")
        btn_layout.addWidget(self.login_btn)
        btn_layout.addWidget(self.register_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        note = QLabel("<i>Nota: registro en memoria (no persistente)</i>")
        layout.addWidget(note)

        self.setLayout(layout)

        self.login_btn.clicked.connect(self.attempt_login)
        self.register_btn.clicked.connect(self.attempt_register)
        self.cancel_btn.clicked.connect(self.reject)

        self.result_username = None

    def attempt_login(self):
        user = self.user_edit.text().strip()
        pwd = self.pwd_edit.text()
        if not user or not pwd:
            QMessageBox.warning(self, "Datos faltantes", "Introduce usuario y contraseña.")
            return
        if user in self._users and self._users[user] == pwd:
            self.result_username = user
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "Usuario o contraseña incorrectos.")

    def attempt_register(self):
        user = self.user_edit.text().strip()
        pwd = self.pwd_edit.text()
        if not user or not pwd:
            QMessageBox.warning(self, "Datos faltantes", "Introduce usuario y contraseña para registrar.")
            return
        if user in self._users:
            QMessageBox.critical(self, "Registro", "El usuario ya existe (en memoria).")
            return
        self._users[user] = pwd
        QMessageBox.information(self, "Registro", "Usuario creado en memoria. Ahora puedes iniciar sesión.")
