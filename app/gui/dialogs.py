import re
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QHBoxLayout, QPushButton, QLabel, QMessageBox
)
from PyQt6.QtCore import Qt

USER_RE = re.compile(r"^[^\s]{3,32}$")


class RegisterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Registrar nuevo usuario")
        self.setModal(True)
        self.resize(380, 180)

        layout = QVBoxLayout()
        form = QFormLayout()

        self.user_edit = QLineEdit()
        self.user_edit.setPlaceholderText("usuario (sin espacios, 3+ caracteres)")
        self.pwd_edit = QLineEdit()
        self.pwd_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd_confirm = QLineEdit()
        self.pwd_confirm.setEchoMode(QLineEdit.EchoMode.Password)

        form.addRow("Usuario:", self.user_edit)
        form.addRow("Contraseña:", self.pwd_edit)
        form.addRow("Confirmar contraseña:", self.pwd_confirm)
        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton("Crear")
        self.cancel_btn = QPushButton("Cancelar")
        btn_layout.addStretch()
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)

    def get_data(self):
        return self.user_edit.text().strip(), self.pwd_edit.text(), self.pwd_confirm.text()


class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Login")
        self.setModal(True)
        self.resize(400, 170)

        self._users = {"admin": "admin"}

        layout = QVBoxLayout()
        form = QFormLayout()
        self.user_edit = QLineEdit()
        self.user_edit.setPlaceholderText("usuario")
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
        self.register_btn.clicked.connect(self.open_register)
        self.cancel_btn.clicked.connect(self.reject)

        self.result_username = None

    def attempt_login(self):
        user = self.user_edit.text().strip()
        pwd = self.pwd_edit.text()
        if not user or not pwd:
            QMessageBox.warning(self, "Datos faltantes", "Introduce usuario y contraseña.")
            return
        if user not in self._users:
            QMessageBox.critical(self, "Error", "No existe ese usuario.")
            return
        if self._users[user] != pwd:
            QMessageBox.critical(self, "Error", "Contraseña incorrecta.")
            return

        self.result_username = user
        self.accept()

    def open_register(self):
        dlg = RegisterDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        user, pwd, pwd_confirm = dlg.get_data()
        user = user.strip()

        if not user or not pwd or not pwd_confirm:
            QMessageBox.warning(self, "Datos faltantes", "Rellena usuario, contraseña y confirmar.")
            return
        if not USER_RE.match(user):
            QMessageBox.warning(self, "Usuario inválido", "El usuario no debe contener espacios y debe tener entre 3 y 32 caracteres.")
            return
        if len(pwd) < 6:
            QMessageBox.warning(self, "Contraseña débil", "La contraseña debe tener al menos 6 caracteres.")
            return
        if pwd != pwd_confirm:
            QMessageBox.warning(self, "Error", "Las contraseñas no coinciden.")
            return
        if user in self._users:
            QMessageBox.critical(self, "Registro", "El usuario ya existe (en memoria).")
            return

        self._users[user] = pwd
        QMessageBox.information(self, "Registro", "Cuenta creada en memoria. Ahora puedes iniciar sesión.")
