# app/controllers/main_controller.py
import logging
from PyQt6 import uic
from PyQt6.QtWidgets import QMainWindow

logger = logging.getLogger(__name__)

class MainController(QMainWindow):
    def __init__(self, username=None):
        super().__init__()
        # Import MainWindow lazily to avoid import-time failures when some
        # submodules are not yet available. This makes the controller more
        # robust during application startup and when running in different
        # environments.
        ProtoboardWindow = None
        try:
            from app.gui.main_window import MainWindow as ProtoboardWindow
        except Exception:
            logger.warning("No se pudo importar app.gui.main_window", exc_info=True)

        logger.debug("ProtoboardWindow is: %s", ProtoboardWindow)
        if ProtoboardWindow is not None:
            try:
                logger.debug("Instanciando ProtoboardWindow con usuario: %s", username)
                self.protoboard = ProtoboardWindow(username=username)
                logger.debug("Mostrando ProtoboardWindow")
                self.protoboard.show()
            except Exception:
                logger.exception("Error creando/mostrando ProtoboardWindow")
            # Cerramos este QMainWindow ya que no hace falta
            self.close()
            return

        # Fallback: si no se pudo importar la MainWindow compleja, cargar UI simple
        try:
            uic.loadUi("app/gui/main_window.ui", self)
        except Exception:
            # si tampoco existe el ui, simplemente no hacemos nada visible
            return

        # Widgets de la UI (fallback)
        try:
            self.label = self.findChild(type(self.findChild), "label")
        except Exception:
            self.label = None

        # Personalizar bienvenida si hay label
        if username and self.label:
            try:
                self.label.setText(f"Bienvenido {username} 🚀")
            except Exception:
                pass
