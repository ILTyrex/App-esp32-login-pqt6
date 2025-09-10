# Login.py
"""
Módulo de autenticación:
- init_db(), create_user(), check_credentials()
- LoginDialog (PyQt6)
"""

import os
import sqlite3
from datetime import datetime
import hashlib
import binascii

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QMessageBox, QLabel
)

DB_FILE = "users.db"

def hash_password(password: str, salt: bytes = None) -> str:
    if salt is None:
        salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100_000)
    return f"{binascii.hexlify(salt).decode('ascii')}${binascii.hexlify(dk).decode('ascii')}"

def verify_password(stored: str, provided_password: str) -> bool:
    try:
        salt_hex, hash_hex = stored.split('$', 1)
        salt = binascii.unhexlify(salt_hex)
        new_hash = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), salt, 100_000)
        return binascii.hexlify(new_hash).decode('ascii') == hash_hex
    except Exception:
        return False

# ---------- Base de datos ----------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        pwd TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM users")
    count = cur.fetchone()[0]
    if count == 0:
        default_hash = hash_password("admin")
        cur.execute("INSERT INTO users (username, pwd, created_at) VALUES (?, ?, ?)",
                    ("admin", default_hash, datetime.now().isoformat()))
        conn.commit()
    conn.close()

def create_user(username: str, password: str) -> (bool, str):
    username = username.strip()
    if not username or not password:
        return False, "Usuario y contraseña no pueden estar vacíos."
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    try:
        pwdhash = hash_password(password)
        cur.execute("INSERT INTO users (username, pwd, created_at) VALUES (?, ?, ?)",
                    (username, pwdhash, datetime.now().isoformat()))
        conn.commit()
        return True, "Usuario creado."
    except sqlite3.IntegrityError:
        return False, "El usuario ya existe."
    except Exception as e:
        return False, f"Error: {e}"
    finally:
        conn.close()

def check_credentials(username: str, password: str) -> bool:
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT pwd FROM users WHERE username = ?", (username.strip(),))
    row = cur.fetchone()
    conn.close()
    if row:
        return verify_password(row[0], password)
    return False

# ---------- Dialog de Login (PyQt6) ----------
class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Login")
        self.setModal(True)
        self.resize(360, 160)
        main_layout = QVBoxLayout()
        header = QLabel("<b>Inicia sesión</b>")
        main_layout.addWidget(header)

        form = QFormLayout()
        self.user_edit = QLineEdit()
        self.pwd_edit = QLineEdit()
        self.pwd_edit.setEchoMode(QLineEdit.EchoMode.Password)

        form.addRow("Usuario:", self.user_edit)
        form.addRow("Contraseña:", self.pwd_edit)
        main_layout.addLayout(form)

        btn_layout = QHBoxLayout()
        self.login_btn = QPushButton("Entrar")
        self.register_btn = QPushButton("Registrar")
        self.cancel_btn = QPushButton("Cancelar")
        btn_layout.addWidget(self.login_btn)
        btn_layout.addWidget(self.register_btn)
        btn_layout.addWidget(self.cancel_btn)
        main_layout.addLayout(btn_layout)

        self.setLayout(main_layout)

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
        ok = check_credentials(user, pwd)
        if ok:
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
        ok, msg = create_user(user, pwd)
        if ok:
            QMessageBox.information(self, "Registro", "Usuario creado. Ahora puedes iniciar sesión.")
        else:
            QMessageBox.critical(self, "Registro", msg)
