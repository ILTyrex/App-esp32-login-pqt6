# app/controllers/login_controller.py
from PyQt6 import uic
from PyQt6.QtWidgets import QMainWindow, QMessageBox, QLineEdit, QPushButton, QLabel
from PyQt6.QtCore import QThread, pyqtSignal, QObject
from app.models.usuario import UsuarioModel
from app.controllers.register_controller import RegisterController
from app.controllers.main_controller import MainController
from app.utils.auth_service import verify_password
import logging

logger = logging.getLogger(__name__)

class LoginWorker(QObject):
    finished = pyqtSignal(bool, str)

    def __init__(self, user, pwd):
        super().__init__()
        self.user = user
        self.pwd = pwd
        self.usuario_model = UsuarioModel()

    def run(self):
        try:
            user_row = self.usuario_model.obtener_usuario(self.user)
            if user_row is None:
                self.finished.emit(False, "Usuario no encontrado o error de BD")
                return

            # Comparación en texto plano (luego usar hash seguro)
            if verify_password(user_row.get("contrasena"), self.pwd):
                self.finished.emit(True, f"Bienvenido {self.user} 🚀")
            else:
                self.finished.emit(False, "Usuario o contraseña incorrectos")
        except Exception as e:
            self.finished.emit(False, f"Error en login: {e}")


class LoginController(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("app/gui/login.ui", self)

        # Widgets
        self.inputUser: QLineEdit = self.findChild(QLineEdit, "inputUser")
        self.inputPassword: QLineEdit = self.findChild(QLineEdit, "inputPassword")
        self.btnLogin: QPushButton = self.findChild(QPushButton, "btnLogin")
        self.textRegister: QLabel = self.findChild(QLabel, "textRegister")

        # Conexiones
        self.btnLogin.clicked.connect(self.handle_login)
        self.textRegister.mousePressEvent = self.go_to_register

        # Thread/worker placeholders
        self.thread = None
        self.worker = None

    def handle_login(self):
        username = self.inputUser.text().strip()
        password = self.inputPassword.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Error", "Por favor ingresa usuario y contraseña")
            return

        # Crear thread y worker
        self.thread = QThread(self)
        self.worker = LoginWorker(username, password)
        self.worker.moveToThread(self.thread)

        # Conexiones
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_login_finished)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        # Iniciar hilo
        self.thread.start()

    def on_login_finished(self, success, msg):
        if success:
            QMessageBox.information(self, "Éxito", msg)
            # Crear la controller principal. `MainController` internamente crea/mostrar
            # la ventana real del protoboard, por lo que no necesitamos llamar a show()
            try:
                # Primero intentamos crear la MainWindow directamente (más robusto)
                try:
                    from app.gui.main_window import MainWindow
                    self.protoboard = MainWindow(username=self.inputUser.text().strip())
                    self.protoboard.show()
                    try:
                        self.protoboard.raise_()
                        self.protoboard.activateWindow()
                    except Exception:
                        pass
                    # mantener referencia y ocultar login
                    self.hide()
                    return
                except Exception as e:
                    logger.warning("No se pudo crear MainWindow directamente: %s", e)

                
                self.main_window = MainController(username=self.inputUser.text().strip())
                
            except Exception as e:
                logger.exception("Excepción al crear MainController")
            # Si no se creó ninguna ventana visible, avisar al usuario
            if not getattr(self, 'protoboard', None) and not getattr(self, 'main_window', None):
                QMessageBox.critical(self, "Error", "No se pudo abrir el panel principal. Revisa la consola para más detalles.")
            else:
                # si alguna ventana fue creada por MainController, intentamos asegurar que esté visible
                try:
                    if getattr(self, 'main_window', None) and getattr(self.main_window, 'protoboard', None):
                        w = self.main_window.protoboard
                        w.show()
                        try:
                            w.raise_()
                            w.activateWindow()
                        except Exception:
                            pass
                        self.hide()
                except Exception:
                    pass
        else:
            QMessageBox.critical(self, "Error", msg)

    def go_to_register(self, event):
        self.register_window = RegisterController()
        self.register_window.show()
        self.hide()
