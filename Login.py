# Login.py
import re
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QHBoxLayout, QPushButton, QLabel, QMessageBox
)
from PyQt6.QtCore import Qt

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

class RegisterDialog(QDialog):
    """Diálogo simple para registrar con correo + contraseña + confirmar."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Registrar nuevo usuario")
        self.setModal(True)
        self.resize(380, 180)

        layout = QVBoxLayout()
        form = QFormLayout()

        self.email_edit = QLineEdit()
        self.pwd_edit = QLineEdit()
        self.pwd_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd_confirm = QLineEdit()
        self.pwd_confirm.setEchoMode(QLineEdit.EchoMode.Password)

        form.addRow("Correo:", self.email_edit)
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
        """Devuelve (email, pwd, pwd_confirm)"""
        return self.email_edit.text().strip(), self.pwd_edit.text(), self.pwd_confirm.text()


class LoginDialog(QDialog):
    """
    Login simple en memoria. Usuarios se mantienen en self._users (dict).
    Clave: correo (en minúsculas) -> contraseña en texto (solo para demo).
    Usuario por defecto: admin@example.com / admin123
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Login")
        self.setModal(True)
        self.resize(400, 170)

        # usuarios en memoria: email -> password
        self._users = {"admin@example.com": "admin123"}

        layout = QVBoxLayout()
        form = QFormLayout()
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("correo@ejemplo.com")
        self.pwd_edit = QLineEdit()
        self.pwd_edit.setEchoMode(QLineEdit.EchoMode.Password)

        form.addRow("Correo:", self.email_edit)
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

        self.result_username = None  # contendrá el correo si login OK

    # ---------- Login ----------
    def attempt_login(self):
        email = self.email_edit.text().strip().lower()
        pwd = self.pwd_edit.text()
        if not email or not pwd:
            QMessageBox.warning(self, "Datos faltantes", "Introduce correo y contraseña.")
            return
        if email not in self._users:
            QMessageBox.critical(self, "Error", "No existe ese usuario.")
            return
        if self._users[email] != pwd:
            QMessageBox.critical(self, "Error", "Contraseña incorrecta.")
            return

        self.result_username = email
        self.accept()

    # ---------- Registro ----------
    def open_register(self):
        dlg = RegisterDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        email, pwd, pwd_confirm = dlg.get_data()
        email = email.strip().lower()

        # Validaciones
        if not email or not pwd or not pwd_confirm:
            QMessageBox.warning(self, "Datos faltantes", "Rellena correo, contraseña y confirmar.")
            return
        if not EMAIL_RE.match(email):
            QMessageBox.warning(self, "Correo inválido", "Introduce un correo válido (ej: usuario@dominio.com).")
            return
        if len(pwd) < 6:
            QMessageBox.warning(self, "Contraseña débil", "La contraseña debe tener al menos 6 caracteres.")
            return
        if pwd != pwd_confirm:
            QMessageBox.warning(self, "Error", "Las contraseñas no coinciden.")
            return
        if email in self._users:
            QMessageBox.critical(self, "Registro", "El correo ya está registrado (en memoria).")
            return

        # Guardar en memoria
        self._users[email] = pwd
        QMessageBox.information(self, "Registro", "Cuenta creada en memoria. Ahora puedes iniciar sesión.")

