# app/workers/db_worker.py
from PyQt6.QtCore import QObject, pyqtSignal
from app.models.usuario import UsuarioModel

class DBWorker(QObject):
    finished = pyqtSignal(bool, str)

    def __init__(self, user, pwd):
        super().__init__()
        self.user = user
        self.pwd = pwd

    def run(self):
        try:
            usuario_model = UsuarioModel()
            ok, msg = usuario_model.crear_usuario(self.user, self.pwd)
            self.finished.emit(ok, msg)
        except Exception as e:
            self.finished.emit(False, f"Error inesperado: {e}")
