# app/controllers/main_controller.py
from PyQt6 import uic
from PyQt6.QtWidgets import QMainWindow

# Importa la MainWindow real (panel protoboard). Preferimos cargarla
# directamente desde `main_window.py` para evitar ciclos de importación
# que se producen si cargamos `python.py` (que a su vez importa controllers).
try:
    from main_window import MainWindow as ProtoboardWindow
except Exception:
    try:
        from python import MainWindow as ProtoboardWindow
    except Exception:
        ProtoboardWindow = None


class MainController(QMainWindow):
    def __init__(self, username=None):
        super().__init__()
        # Intentamos abrir la ventana del protoboard.
        # Si no se puede (ProtoboardWindow es None) cargamos el UI simple por compatibilidad.
        if ProtoboardWindow is not None:
            # Creamos directamente la ventana completa y la mostramos.
            self.protoboard = ProtoboardWindow(username=username)
            self.protoboard.show()
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
